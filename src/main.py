"""Main Execution Pipeline for Lottery Intelligence Platform."""
import sys
from datetime import datetime
from src.core.logger import get_logger
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor

logger = get_logger("Main")

def run_pipeline():
    logger.info("Starting Lottery Intelligence Pipeline...")

    # 1. Fetch Latest Draw Data
    importer = EurojackpotImporter()
    draws = importer.fetch_latest_draws()
    db = DBManager()

    if draws:
        latest = draws[0]
        draw_date = latest.get("draw_date", "")
        if not draw_date:
            logger.error("Fetched draw has no date.")
            sys.exit(1)
        
        try:
            datetime.strptime(draw_date, "%Y-%m-%d")
        except ValueError:
            logger.error("Invalid draw_date format: %s", draw_date)
            sys.exit(1)

        logger.info("Fetched draw for %s: primary=%s euro=%s",
                    draw_date, latest.get("primary_numbers"), latest.get("euro_numbers"))
        
        inserted = db.insert_draw(latest)
        if inserted:
            logger.info("Successfully saved latest draw to database.")
        else:
            logger.info("Draw %s already exists in database.", draw_date)

    # 2. Run Analytics & Predictions
    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)

    pred_result = predictor.predict_candidate_set(primary_count=7, euro_count=3)

    stats = {
        "total_draws": len(db.get_all_draws())
    }

    # 3. Send Email Notification (if configured)
    try:
        from src.notifications.email_sender import LotteryEmailSender
        sender = LotteryEmailSender()
        sender.send_prediction({
            "prediction_for_date": "Next Draw",
            "primary_candidates": pred_result["primary_candidates"],
            "euro_candidates": pred_result["euro_candidates"],
            "method": pred_result.get("method"),
            "confidence": pred_result.get("confidence", {})
        }, stats)
    except Exception as e:
        logger.warning("Email notification skipped or failed: %s", e)

    # 4. Generate Dashboard Report
    try:
        from src.analytics.dashboard import SuccessDashboard
        dash = SuccessDashboard(db)
        dash.generate_html_report()
    except Exception as e:
        logger.warning("Dashboard generation failed: %s", e)

    logger.info("Pipeline execution completed successfully.")

if __name__ == "__main__":
    run_pipeline()
