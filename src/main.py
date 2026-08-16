"""Main Execution Pipeline for Lottery Intelligence Platform."""
import sys
from datetime import datetime, timedelta
from src.core.logger import get_logger
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor

logger = get_logger("Main")

def get_next_draw_date():
    """Calculate the next Eurojackpot draw date (Tuesday or Friday)."""
    today = datetime.now()
    weekday = today.weekday()  # Monday is 0, Tuesday is 1, Friday is 4
    hour = today.hour

    # Eurojackpot draws occur on Tuesdays (1) and Fridays (4) around 21:00-22:00
    if weekday == 1 and hour < 21:
        # Tuesday before draw -> draw is today
        target = today
    elif weekday == 4 and hour < 21:
        # Friday before draw -> draw is today
        target = today
    else:
        # Find the next Tuesday or Friday
        days_ahead = 1
        while True:
            next_day = today + timedelta(days=days_ahead)
            if next_day.weekday() in (1, 4):
                target = next_day
                break
            days_ahead += 1

    return target.strftime("%Y-%m-%d")

def run_pipeline():
    logger.info("Starting Lottery Intelligence Pipeline...")

    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)

    # 1. Fetch & Update Draw Data (Ensuring History Exists)
    logger.info("Checking and fetching draw history...")
    
    # Πρώτα εκτελούμε συγχρονισμό/backfill αν η βάση είναι άδεια ή πίσω σε κληρώσεις
    if hasattr(importer, 'sync_history'):
        importer.sync_history()
    else:
        draw = importer.fetch_latest_draw()
        if draw:
            draw_date = draw.get("draw_date", "")
            inserted = db.insert_draw(draw)
            if inserted:
                logger.info("Successfully saved latest draw (%s) to database.", draw_date)
            else:
                logger.info("Draw %s already exists in database.", draw_date)
        else:
            logger.warning("No draw returned from importer.")

    # 2. Guard Check: Verify Database Contains Data
    all_draws = db.get_all_draws()
    total_draws_count = len(all_draws) if all_draws else 0
    logger.info("Total draws in database: %d", total_draws_count)

    if total_draws_count == 0:
        logger.error("CRITICAL: Database is completely empty! Predictions cannot be calculated.")
        sys.exit(1)

    # 3. Run Analytics & Predictions
    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)

    pred_result = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    
    # Έλεγχος εγκυρότητας προβλέψεων (Αποφυγή αποστολής 0/None)
    primary_cands = pred_result.get("primary_candidates", [])
    euro_cands = pred_result.get("euro_candidates", [])

    if not primary_cands or all(v == 0 for v in primary_cands):
        logger.error("Predictor returned empty or zero candidates! Check Frequency/Pattern Analyzers.")

    next_draw = get_next_draw_date()

    # Save prediction to database
    db.insert_prediction({
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw,
        "predicted_primary": primary_cands,
        "predicted_euro": euro_cands,
        "method": pred_result.get("method", "Hybrid-Probability"),
        "confidence": pred_result.get("confidence", {})
    })

    stats = {
        "total_draws": total_draws_count
    }

    # 4. Send Email Notification
    try:
        from src.notifications.email_sender import LotteryEmailSender
        sender = LotteryEmailSender()
        sender.send_prediction({
            "prediction_for_date": next_draw,
            "primary_candidates": primary_cands,
            "euro_candidates": euro_cands,
            "method": pred_result.get("method", "Hybrid-Probability"),
            "confidence": pred_result.get("confidence", {})
        }, stats)
        logger.info("Email prediction notification sent successfully.")
    except Exception as e:
        logger.warning("Email notification skipped or failed: %s", e)

    # 5. Generate Dashboard Report
    try:
        from src.analytics.dashboard import SuccessDashboard
        dash = SuccessDashboard(db)
        dash.generate_html_report()
        logger.info("Dashboard report generated successfully.")
    except Exception as e:
        logger.warning("Dashboard generation failed: %s", e)

    logger.info("Pipeline execution completed successfully.")

if __name__ == "__main__":
    run_pipeline()
