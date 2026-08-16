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
    logger.info("=== Starting Eurojackpot Intelligence Pipeline ===")

    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)

    # 1. Φέρνουμε τις πρόσφατες κληρώσεις & ενημερώνουμε τη βάση
    logger.info("1. Syncing draw history from OPAP API...")
    importer.sync_history()

    all_draws = db.get_all_draws()
    if not all_draws:
        logger.error("CRITICAL: Database has no draws. Cannot proceed.")
        sys.exit(1)

    latest_draw = all_draws[0]
    logger.info("Latest Draw in DB: Date %s | Primary: %s | Euro: %s",
                latest_draw.get("draw_date"), 
                latest_draw.get("primary_numbers"), 
                latest_draw.get("euro_numbers"))

    # 2. ΕΛΕΓΧΟΣ ΕΠΙΤΥΧΙΑΣ: Σύγκριση προηγούμενης πρόβλεψης με τη νέα κλήρωση
    logger.info("2. Checking prediction performance against latest draw...")
    if hasattr(db, 'validate_latest_prediction'):
        db.validate_latest_prediction(latest_draw)

    # 3. ΑΝΑΛΥΣΗ & ΝΕΑ ΠΡΟΒΛΕΨΗ
    logger.info("3. Generating prediction for upcoming draw...")
    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)

    pred_result = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    
    primary_cands = pred_result.get("primary_candidates", [])
    euro_cands = pred_result.get("euro_candidates", [])

    if not primary_cands or all(v == 0 for v in primary_cands):
        logger.error("Predictor returned invalid zero candidates! Check analyzers.")

    next_draw_date = importer.get_next_draw_date()

    # Αποθήκευση της νέας πρόβλεψης στη βάση
    db.insert_prediction({
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw_date,
        "predicted_primary": primary_cands,
        "predicted_euro": euro_cands,
        "method": pred_result.get("method", "Hybrid-Probability"),
        "confidence": pred_result.get("confidence", {})
    })
    logger.info("Saved New Prediction for %s: Primary %s | Euro %s", next_draw_date, primary_cands, euro_cands)

    # 4. ΑΠΟΣΤΟΛΗ EMAIL & REPORTS
    try:
        from src.notifications.email_sender import LotteryEmailSender
        sender = LotteryEmailSender()
        stats = {
            "total_draws": len(all_draws),
            "latest_draw": latest_draw
        }
        sender.send_prediction({
            "prediction_for_date": next_draw_date,
            "primary_candidates": primary_cands,
            "euro_candidates": euro_cands,
            "method": pred_result.get("method", "Hybrid-Probability")
        }, stats)
        logger.info("Email notification sent successfully.")
    except Exception as e:
        logger.warning("Email notification skipped/failed: %s", e)

    # 5. ΔΗΜΙΟΥΡΓΙΑ DASHBOARD
    try:
        from src.analytics.dashboard import SuccessDashboard
        dash = SuccessDashboard(db)
        dash.generate_html_report()
        logger.info("Dashboard report generated successfully.")
    except Exception as e:
        logger.warning("Dashboard generation failed: %s", e)

    logger.info("=== Pipeline Completed Successfully ===")

if __name__ == "__main__":
    run_pipeline()
