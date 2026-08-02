"""
Main entry point for the Lottery Intelligence Platform.

This script coordinates the data pipeline: initialization, fetching Eurojackpot
data, validation, and storage into the SQLite database.
"""

import sys
from pathlib import Path

# Add project root to path for smooth package imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.database.database_manager import DatabaseManager
from src.importers.eurojackpot_importer import EuroJackpotImporter
from src.utils.validator import DataValidator

# Initialize central logger
logger = get_logger("MainPipeline")


def run_pipeline(
    db_path: str = "data/lottery.db", schema_path: str = "database/schema.sql"
) -> None:
    """Executes the complete data extraction, validation, and loading pipeline.

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

        if not raw_draws:
            logger.warning("No draw data retrieved from importer.")
            return

        logger.info(f"Retrieved {len(raw_draws)} raw draws.")

        # Step 3: Validate and insert draw records
        inserted_count = 0
        skipped_count = 0

        for draw in raw_draws:
            # Validate structure and values
            is_valid, err_msg = DataValidator.validate_draw(draw)

            if not is_valid:
                logger.warning(
                    f"Skipping invalid draw (Date: {draw.get('draw_date')}): {err_msg}"
                )
                skipped_count += 1
                continue

            # Check if record already exists in database
            draw_date = draw["draw_date"]
            if db_manager.table_exists("eurojackpot_draws"):
                query = "SELECT id FROM eurojackpot_draws WHERE draw_date = ?"
                existing = db_manager.fetch_one(query, (draw_date,))
                if existing:
                    skipped_count += 1
                    continue

            # Insert valid draw into DB
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

        logger.info("==================================================")
        logger.info(
            f"Pipeline Execution Completed: {inserted_count} inserted, {skipped_count} skipped/duplicates."
        )
        logger.info("==================================================")

    except Exception as e:
        logger.error(f"Critical error during pipeline execution: {str(e)}")
        raise


if __name__ == "__main__":
    run_pipeline()
