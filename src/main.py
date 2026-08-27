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

    # 1. Συγχρονισμός ιστορικού
    logger.info("1. Syncing draw history...")
    importer.sync_history()

    # 2. Ανάκτηση και αποθήκευση της τελευταίας κλήρωσης
    logger.info("2. Fetching latest draw...")
    latest = importer.fetch_latest_draw()

    if latest:
        inserted = db.insert_draw(latest)
        if inserted:
            logger.info("New draw saved: %s | Primary: %s | Euro: %s",
                        latest["draw_date"], latest["primary_numbers"], latest["euro_numbers"])
            # 🔮 Αξιολόγηση της προηγούμενης πρόβλεψης ΜΟΝΟ αν μπήκε νέα κλήρωση
            db.validate_latest_prediction(latest)
        else:
            logger.info("Draw %s already exists in database.", latest["draw_date"])
    else:
        logger.warning("Could not fetch latest draw. Using existing database data.")

    # 3. Έλεγχος διαθεσιμότητας δεδομένων
    all_draws = db.get_all_draws()
    if not all_draws:
        logger.error("CRITICAL: Database is empty. Cannot generate predictions.")
        sys.exit(1)

    latest_draw = all_draws[0]
    logger.info("Latest draw in DB: %s | Primary: %s | Euro: %s",
                latest_draw["draw_date"],
                latest_draw["primary_numbers"],
                latest_draw["euro_numbers"])

    # 4. Αναλύσεις & Παραγωγή Πρόβλεψης
    logger.info("4. Generating prediction for next draw...")
    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)

    pred_result = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    primary_cands = pred_result.get("primary_candidates", [])
    euro_cands = pred_result.get("euro_candidates", [])

    if not primary_cands:
        logger.error("Predictor returned empty candidates!")
        sys.exit(1)

    next_draw_date = importer.get_next_draw_date()

    # Αποθήκευση πρόβλεψης στη βάση
    db.insert_prediction({
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw_date,
        "predicted_primary": primary_cands,
        "predicted_euro": euro_cands,
        "method": pred_result.get("method", "composite_freq_delay"),
        "confidence": pred_result.get("confidence", {})
    })
    logger.info("Saved prediction for %s: Primary %s | Euro %s",
                next_draw_date, primary_cands, euro_cands)

    # 5. Αποστολή Email
    logger.info("5. Sending email notification...")
    try:
        from src.notifications.email_sender import LotteryEmailSender
        sender = LotteryEmailSender()
        stats = {"total_draws": len(all_draws), "latest_draw": latest_draw}
        sender.send_prediction({
            "prediction_for_date": next_draw_date,
            "primary_candidates": primary_cands,
            "euro_candidates": euro_cands,
            "method": pred_result.get("method", "composite_freq_delay"),
            "confidence": pred_result.get("confidence", {})
        }, stats)
    except Exception as e:
        logger.warning("Email failed: %s", e)

    # 6. Δημιουργία Dashboard Report
    logger.info("6. Generating dashboard...")
    try:
        from src.analytics.dashboard import SuccessDashboard
        dash = SuccessDashboard(db)
        dash.generate_html_report()
    except Exception as e:
        logger.warning("Dashboard failed: %s", e)

    logger.info("=== Pipeline Completed Successfully ===")

if __name__ == "__main__":
    run_pipeline()
