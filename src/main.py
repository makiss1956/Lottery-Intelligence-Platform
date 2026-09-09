"""
Main Execution Pipeline for Lottery Intelligence Platform.
"""
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

# Path setup for standalone script execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.core.logger import get_logger
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter

logger = get_logger("Main")


def send_prediction_email(prediction_data: dict, stats: dict) -> bool:
    """Send structured email prediction using environment settings."""
    email_user = os.getenv("LOTTERY_EMAIL_USER")
    email_to = os.getenv("LOTTERY_EMAIL_TO")
    email_pass = os.getenv("LOTTERY_EMAIL_PASS")

    if not all([email_user, email_to, email_pass]):
        logger.warning("Missing email credentials. Skipping notification.")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = email_user
    msg["To"] = email_to
    msg["Subject"] = f"Eurojackpot Prediction — {prediction_data['for_draw_date']}"

    body = f"""Lottery Intelligence Platform Prediction Report
======================================================

Target Draw Date: {prediction_data['for_draw_date']}
Prediction Generated: {prediction_data['prediction_date']}

Primary Candidates (7): {', '.join(map(str, prediction_data['predicted_primary']))}
Euro Candidates (3):    {', '.join(map(str, prediction_data['predicted_euro']))}

Method: {prediction_data.get('method', 'hybrid_ensemble')}

Database Statistics:
- Total Historical Draws: {stats['total_draws']}
- Latest Stored Draw: {stats['latest_draw']['draw_date']}
"""

    val = stats.get("validation")
    if val:
        body += f"""
Previous Draw Validation ({val.get('draw_date', 'N/A')}):
- Primary Hits: {val.get('main_hits_count', 0)}/5
- Euro Hits:    {val.get('euro_hits_count', 0)}/2
- Hit Score:    {val.get('score_percentage', 0.0):.2f}%
"""

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        logger.info("Email prediction delivered to %s", email_to)
        return True
    except Exception as exc:
        logger.error("Failed to send prediction email: %s", exc)
        return False


def run_pipeline() -> None:
    """Execute full data ingestion, backtesting, prediction, and reporting."""
    logger.info("==================================================")
    logger.info("STARTING LOTTERY INTELLIGENCE PIPELINE")
    logger.info("==================================================")

    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)

    # STEP 1: Sync local history
    logger.info("STEP 1: Synchronizing history from CSV...")
    inserted_csv = importer.sync_history()

    # STEP 2: Fetch newest draw
    logger.info("STEP 2: Fetching latest draw...")
    latest = importer.fetch_latest_draw()
    if latest:
        db.insert_draw(latest)

    all_draws = db.get_all_draws()
    if not all_draws:
        logger.error("FATAL: Database contains no draw records.")
        sys.exit(1)

    latest_draw = all_draws[0]

    # STEP 3: Validate performance against last draw
    logger.info("STEP 3: Validating previous draw performance...")
    validation_result = db.validate_prediction_for_draw(latest_draw)

    # STEP 4: Determine next target draw date
    next_draw_date = importer.get_next_draw_date()
    logger.info("STEP 4: Target draw date set to %s", next_draw_date)

    # STEP 5: Run prediction engine
    logger.info("STEP 5: Generating Hybrid Ensemble predictions...")
    predictor = ProbabilityPredictor(db_manager=db)
    prediction = predictor.generate_prediction(for_draw_date=next_draw_date)

    # STEP 6: Save prediction
    logger.info("STEP 6: Persisting prediction to database...")
    saved = db.insert_prediction(prediction)

    # STEP 7: Dispatch email report
    logger.info("STEP 7: Dispatching email notifications...")
    stats = {
        "total_draws": db.get_draw_count(),
        "latest_draw": latest_draw,
        "validation": validation_result,
    }
    send_prediction_email(prediction, stats)

    logger.info("==================================================")
    logger.info("PIPELINE EXECUTION COMPLETE")
    logger.info("==================================================")


if __name__ == "__main__":
    run_pipeline()
