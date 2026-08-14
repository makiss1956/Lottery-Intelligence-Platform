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
    weekday = today.weekday()
    hour = today.hour
    
    # Eurojackpot draws: Tuesday (1), Friday (4)
    if weekday == 1 and hour >= 22:
        # After Tuesday draw -> next is Friday
        days_until = 4 - weekday
    elif weekday == 4 and hour >= 22:
        # After Friday draw -> next is Tuesday
        days_until = (7 - weekday) + 1
    elif weekday < 1:
        days_until = 1 - weekday
    elif weekday < 4:
        days_until = 4 - weekday
    else:
        days_until = (7 - weekday) + 1
    
    return (today + timedelta(days=days_until)).strftime("%Y-%m-%d")

def run_pipeline():
    logger.info("Starting Lottery Intelligence Pipeline...")

    db = DBManager()

    # 1. Fetch Latest Draw Data
    importer = EurojackpotImporter(db_manager=db)
    draw = importer.fetch_latest_draw()
    
    if draw:
        draw_date = draw.get("draw_date", "")
        logger.info("Fetched draw for %s: primary=%s euro=%s",
                    draw_date, draw.get("primary_numbers"), draw.get("euro_numbers"))
        inserted = db.insert_draw(draw)
        if inserted:
            logger.info("Successfully saved latest draw to database.")
        else:
            logger.info("Draw %s already exists in database.", draw_date)
    else:
        logger.info("No new draw to fetch.")

    # 2. Run Analytics & Predictions
    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)

    pred_result = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    next_draw = get_next_draw_date()

    # Save prediction to database
    db.insert_prediction({
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw,
        "predicted_primary": pred_result["primary_candidates"],
        "predicted_euro": pred_result["euro_candidates"],
        "method": pred_result.get("method"),
        "confidence": pred_result.get("confidence")
    })

    stats = {
        "total_draws": len(db.get_all_draws())
    }

    # 3. Send Email Notification
    try:
        from src.notifications.email_sender import LotteryEmailSender
        sender = LotteryEmailSender()
        sender.send_prediction({
            "prediction_for_date": next_draw,
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
