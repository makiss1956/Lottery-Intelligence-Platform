"""Main Application Pipeline Entrypoint.

Coordinates:
 1. Data fetching
 2. Persistence check
 3. Evaluation of previous prediction (if unevaluated)
 4. Statistical analysis on updated dataset
 5. New prediction generation
 6. Save prediction to history
"""
import logging
import sys
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lottery_pipeline")

def run_pipeline(force: bool = False) -> None:
    logger.info("=== Lottery Analysis Pipeline Starting ===")

    # 1. Imports
    try:
        from src.importers.eurojackpot_importer import EuroJackpotImporter
        from src.database.db_manager import DBManager
        from src.analytics.frequency_analyzer import FrequencyAnalyzer
        from src.analytics.predictor import ProbabilityPredictor
        from src.core.config import get_config
        from src.utils.validator import validate_draw
    except ImportError as e:
        logger.error("Import error: %s", e)
        sys.exit(1)

    cfg = get_config()
    db_path = cfg.get("database", "path", default="data/lottery_data.db")

    db = DBManager(db_path)
    importer = EuroJackpotImporter()
    analyzer = FrequencyAnalyzer(db)
    predictor = ProbabilityPredictor(analyzer)

    # 2. Fetch latest draw
    try:
        latest = importer.fetch_latest_draw()
    except Exception as e:
        logger.error("Fetch failed: %s", e)
        sys.exit(1)

    if not latest:
        logger.warning("No draw data fetched. Exiting.")
        return

    if not validate_draw(latest):
        logger.error("Fetched draw failed validation: %s", latest)
        sys.exit(1)

    draw_date = latest.get("draw_date", "")
    logger.info("Fetched draw for %s: primary=%s euro=%s",
                draw_date, latest["primary_numbers"], latest["euro_numbers"])

    # 3. Check if already in DB
    if db.draw_exists(draw_date) and not force:
        logger.info("Draw %s already in database. Skipping.", draw_date)
        print(f"Pipeline completed: Draw {draw_date} already exists.")
        return

    # 4. Insert new draw
    is_new = db.insert_draw(latest)
    if not is_new and not force:
        logger.info("Draw was not new (duplicate). Exiting.")
        return

    logger.info("New draw inserted: %s", draw_date)

    # 5. Evaluate previous prediction BEFORE generating new one
    evaluation = None
    try:
        prev_pred = db.get_unevaluated_prediction()
        if prev_pred:
            logger.info("Evaluating previous prediction id=%s for date %s",
                        prev_pred["id"], prev_pred["prediction_for_date"])
            db.evaluate_prediction(prev_pred["id"], latest)
            # Reload evaluated record
            with db.get_connection() as conn:
                row = conn.execute("SELECT * FROM predictions WHERE id = ?", (prev_pred["id"],)).fetchone()
                if row:
                    evaluation = dict(row)
                    # Parse lists for display
                    if evaluation.get("matched_main"):
                        evaluation["matched_main"] = [int(x) for x in evaluation["matched_main"].split(",") if x.strip()]
                    if evaluation.get("matched_euro"):
                        evaluation["matched_euro"] = [int(x) for x in evaluation["matched_euro"].split(",") if x.strip()]
        else:
            logger.info("No unevaluated prediction found.")
    except Exception as e:
        logger.error("Evaluation error: %s", e)

    # 6. Refresh analyzer cache and generate stats
    analyzer.cache.clear()
    stats = analyzer.get_stats_summary()

    # 7. Generate NEW prediction for NEXT draw
    try:
        pred_result = predictor.predict_candidate_set(
            primary_count=cfg.get("analytics", "default_primary_candidates", default=7),
            euro_count=cfg.get("analytics", "default_euro_candidates", default=3)
        )
    except Exception as e:
        logger.error("Prediction generation failed: %s", e)
        sys.exit(1)

    # 8. Determine next draw date (Tue/Fri)
    from datetime import datetime, timedelta
    today = datetime.strptime(draw_date, "%Y-%m-%d")
    weekday = today.weekday()
    if weekday == 1:  # Tuesday -> Friday
        next_date = today + timedelta(days=3)
    elif weekday == 4:  # Friday -> Tuesday
        next_date = today + timedelta(days=4)
    else:
        # Fallback: just add 3 days
        next_date = today + timedelta(days=3)
    next_draw_date = next_date.strftime("%Y-%m-%d")

    # 9. Save prediction
    try:
        pred_id = db.save_prediction({
            "prediction_for_date": next_draw_date,
            "predicted_primary": pred_result["primary_candidates"],
            "predicted_euro": pred_result["euro_candidates"],
            "method": pred_result.get("method", "frequency_7_3")
        })
        logger.info("Saved prediction id=%s for next draw %s", pred_id, next_draw_date)
    except Exception as e:
        logger.error("Failed to save prediction: %s", e)

    # 10. Print report
    print("=" * 60)
    print("🚀 PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f" New draw: {draw_date}")
    print(f" Numbers: {latest['primary_numbers']} + {latest['euro_numbers']}")
    if evaluation:
        print(f" Previous prediction scored: {evaluation.get('score_percentage','N/A')}%")
        print(f" Matched main: {evaluation.get('matched_main', [])}")
        print(f" Matched euro: {evaluation.get('matched_euro', [])}")
    print(f" New prediction saved for: {next_draw_date}")
    print(f" Primary candidates: {pred_result['primary_candidates']}")
    print(f" Euro candidates: {pred_result['euro_candidates']}")
    print(f" Total draws in DB: {db.get_draw_count()}")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force run even if draw exists")
    args = parser.parse_args()
    run_pipeline(force=args.force)
