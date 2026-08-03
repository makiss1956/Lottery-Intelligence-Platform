"""
Main entry point for the Lottery Intelligence Platform.

Coordinates the complete data pipeline: initialization, fetching Eurojackpot data,
validation, database storage, statistical analysis, probability prediction,
and evaluation.
"""

import sys
from pathlib import Path

# Add project root to path for smooth package imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.core.logger import get_logger
from src.database.database_manager import DatabaseManager
from src.importers.eurojackpot_importer import EuroJackpotImporter
from src.utils.validator import DataValidator

# Initialize central logger
logger = get_logger("MainPipeline")


def run_pipeline(
    db_path: str = "data/lottery.db", schema_path: str = "database/schema.sql"
) -> None:
    """Executes the complete data extraction, analysis, and prediction pipeline.

    Args:
        db_path (str): Path to the SQLite database file.
        schema_path (str): Path to the SQL schema initialization file.
    """
    logger.info("==================================================")
    logger.info("Starting Lottery Intelligence Platform Pipeline")
    logger.info("==================================================")

    try:
        # Step 1: Initialize Database Manager
        db_manager = DatabaseManager(db_path=db_path, schema_path=schema_path)
        db_manager.initialize_database()
        logger.info("Database connection and schema verification complete.")

        # Step 2: Fetch raw draw data using EuroJackpot Importer
        importer = EuroJackpotImporter()
        logger.info("Fetching latest Eurojackpot draws...")
        raw_draws = importer.fetch_latest_draws()

        if raw_draws:
            logger.info(f"Retrieved {len(raw_draws)} raw draws.")
            inserted_count = 0
            skipped_count = 0

            for draw in raw_draws:
                is_valid, err_msg = DataValidator.validate_draw(draw)
                if not is_valid:
                    logger.warning(
                        f"Skipping invalid draw ({draw.get('draw_date')}): {err_msg}"
                    )
                    skipped_count += 1
                    continue

                draw_date = draw["draw_date"]
                if db_manager.table_exists("eurojackpot_draws"):
                    query = "SELECT id FROM eurojackpot_draws WHERE draw_date = ?"
                    existing = db_manager.fetch_one(query, (draw_date,))
                    if existing:
                        skipped_count += 1
                        continue

                insert_query = """
                    INSERT INTO eurojackpot_draws 
                    (draw_date, num1, num2, num3, num4, num5, euro1, euro2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    draw["draw_date"],
                    draw["numbers"][0],
                    draw["numbers"][1],
                    draw["numbers"][2],
                    draw["numbers"][3],
                    draw["numbers"][4],
                    draw["euro_numbers"][0],
                    draw["euro_numbers"][1],
                )
                db_manager.execute(insert_query, params)
                inserted_count += 1

            logger.info(
                f"Data Ingestion: {inserted_count} new inserted, {skipped_count} skipped/duplicates."
            )
        else:
            logger.warning("No draw data retrieved from importer.")

        # Step 3: Run Statistical Analytics & Prediction
        logger.info("Running Frequency and Delay Analytics...")
        analyzer = FrequencyAnalyzer(db_manager)

        predictor = ProbabilityPredictor(analyzer)
        candidates = predictor.predict_candidate_set(primary_count=7, euro_count=3)

        logger.info("==================================================")
        logger.info("🎯 STATISTICAL PREDICTION WINDOW FOR NEXT DRAW:")
        logger.info(f"Primary Candidates (7 Numbers) : {candidates['primary_candidates']}")
        logger.info(f"Euro Candidates (3 Numbers)    : {candidates['euro_candidates']}")
        logger.info("==================================================")

        # Step 4: Run Evaluation / Backtest on the last recorded draw
        all_draws = analyzer.fetch_all_draws()
        if all_draws:
            latest_db_draw = all_draws[0]
            actual_draw_formatted = {
                "draw_date": latest_db_draw[0],
                "numbers": list(latest_db_draw[1:6]),
                "euro_numbers": list(latest_db_draw[6:8]),
            }

            evaluation = Backtester.evaluate_prediction(
                predicted_mains=candidates["primary_candidates"],
                predicted_euros=candidates["euro_candidates"],
                actual_draw=actual_draw_formatted,
            )

            logger.info(
                f"Evaluation against last draw ({evaluation['draw_date']}): "
                f"Main Matches = {evaluation['main_hits_count']}/5, "
                f"Target Achieved (>=3) = {evaluation['target_achieved']}"
            )

        logger.info("==================================================")
        logger.info("Pipeline Execution Completed Successfully.")
        logger.info("==================================================")

    except Exception as e:
        logger.error(f"Critical error during pipeline execution: {str(e)}")
        raise


if __name__ == "__main__":
    run_pipeline()
