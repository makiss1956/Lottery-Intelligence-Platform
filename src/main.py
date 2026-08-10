"""
Main Application Pipeline Entrypoint
----------------------------------
Coordinates data fetching, persistence check, statistical analysis, 
prediction generation, and conditional email notification dispatch.
"""

import logging
import sys
from typing import Dict, Any, Optional

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lottery_pipeline")


def run_pipeline() -> None:
    """
    Executes the primary workflow:
    1. Fetch latest draw data from external source.
    2. Check if the draw is new and save to persistent storage.
    3. Run predictions ONLY if new draw data was inserted or if explicitly forced.
    4. Send email notification ONLY when a genuine new draw is processed.
    """
    logger.info("Starting Lottery Analysis Pipeline execution...")

    # 1. Initialization of Modules
    try:
        from src.importers.data_importer import DataImporter
        from src.database.db_manager import DBManager
        from src.statistics_engine.frequency_analyzer import FrequencyAnalyzer
        from src.predictors.probability_predictor import ProbabilityPredictor
        from src.notifications.email_sender import EmailSender

        importer = DataImporter()
        db_manager = DBManager()
        freq_analyzer = FrequencyAnalyzer(database_connection=db_manager)
        predictor = ProbabilityPredictor(freq_analyzer=freq_analyzer)
        email_sender = EmailSender()

    except ImportError as e:
        logger.error("Failed to import required pipeline modules: %s", e)
        sys.exit(1)

    # 2. Fetch Latest Draw
    try:
        if hasattr(importer, "fetch_latest_draw"):
            latest_draw = importer.fetch_latest_draw()
        elif hasattr(importer, "fetch_latest_draws"):
            latest_draw = importer.fetch_latest_draws()
        else:
            logger.error("No valid fetch method found on DataImporter.")
            sys.exit(1)

        if not latest_draw:
            logger.info("No draw data retrieved from importer. Exiting pipeline.")
            return

    except Exception as e:
        logger.error("Error occurred while fetching latest draw: %s", e)
        sys.exit(1)

    # 3. Save Draw & Check Uniqueness (INSERT OR IGNORE Check)
    # Η save_draw / insert_draw επιστρέφει True αν μπήκε νέο εγγραφή, False αν υπήρχε ήδη
    is_new_draw = False
    try:
        if hasattr(db_manager, "save_draw_if_new"):
            is_new_draw = db_manager.save_draw_if_new(latest_draw)
        elif hasattr(db_manager, "insert_draw"):
            is_new_draw = db_manager.insert_draw(latest_draw)
        else:
            # Fallback έλεγχος αν η μέθοδος δεν επιστρέφει boolean
            is_new_draw = True  # Default συμπεριφορά αν δεν υποστηρίζεται ο έλεγχος

    except Exception as e:
        logger.error("Failed to save draw to database: %s", e)
        sys.exit(1)

    # 4. Pipeline Decision Gate (Spam Prevention)
    if not is_new_draw:
        logger.info("Draw %s already exists in the database. No new data processed. Skipping email notification.", 
                    latest_draw.get("draw_number", "Unknown"))
        print("Pipeline Execution Completed: No new draw detected. Email skipped.")
        return

    logger.info("New draw detected (%s)! Proceeding with statistical analysis and notification.", 
                latest_draw.get("draw_number", "Unknown"))

    # 5. Load fresh dataset into Statistics Engine & Run Predictions
    all_draws = db_manager.get_all_draws() if hasattr(db_manager, "get_all_draws") else [latest_draw]
    freq_analyzer.load_draws(all_draws)

    # Generate Candidate Prediction
    prediction_result = predictor.predict_candidate_set(
        primary_numbers=latest_draw.get("primary_numbers", []),
        euro_numbers=latest_draw.get("euro_numbers", [])
    )

    # 6. Send Email Notification ONLY for new draws
    try:
        logger.info("Dispatching email notification for new draw...")
        email_sender.send_prediction_report(
            draw_data=latest_draw,
            prediction_data=prediction_result
        )
        logger.info("Email notification sent successfully.")
    except Exception as e:
        logger.error("Failed to send email notification: %s", e)

    print("Pipeline Execution Completed: New draw processed and notification dispatched.")


if __name__ == "__main__":
    run_pipeline()
