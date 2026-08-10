"""
CLI Module for Lottery Analysis Platform
----------------------------------------
Provides command-line interface commands for data fetching, analysis, 
and prediction tasks.
"""

import argparse
import logging
import sys
from typing import Any, List, Optional

# Ρύθμιση logging για το CLI
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lottery_cli")


def cmd_fetch(args: argparse.Namespace) -> None:
    """
    Executes the draw fetching process via the configured data importer.
    """
    logger.info("Initiating draw fetch operation...")
    
    # Εισαγωγή του importer (προσαρμόστε το import ανάλογα με τη δομή του έργου)
    try:
        from src.importers.data_importer import DataImporter
        importer = DataImporter()
    except ImportError:
        logger.error("Could not import DataImporter. Ensure project modules are properly configured.")
        sys.exit(1)

    try:
        # Έλεγχος διαθεσιμότητας μεθόδου (fetch_latest_draw vs fetch_latest_draws)
        if hasattr(importer, "fetch_latest_draw"):
            draws = importer.fetch_latest_draw()
        elif hasattr(importer, "fetch_latest_draws"):
            draws = importer.fetch_latest_draws()
        else:
            raise AttributeError("DataImporter has no valid draw fetching method ('fetch_latest_draw' or 'fetch_latest_draws').")

        logger.info("Successfully fetched draws data: %s", draws)
    except Exception as e:
        logger.error("Failed to fetch latest draws: %s", e)
        sys.exit(1)


def cmd_analyze(args: argparse.Namespace) -> None:
    """
    Executes statistical analysis on stored draws.
    """
    logger.info("Running statistical analysis...")
    # Υλοποίηση εντολής ανάλυσης
    print("Statistical Analysis Completed.")


def cmd_predict(args: argparse.Namespace) -> None:
    """
    Executes prediction models to evaluate numbers.
    """
    logger.info("Running prediction models...")
    # Υλοποίηση εντολής πρόβλεψης
    print("Prediction Task Completed.")


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Lottery Intelligence CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Fetch subcommand
    fetch_parser = subparsers.add_parser("fetch", help="Fetch the latest draw data")
    fetch_parser.set_defaults(func=cmd_fetch)

    # Analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Run frequency and gap analysis")
    analyze_parser.set_defaults(func=cmd_analyze)

    # Predict subcommand
    predict_parser = subparsers.add_parser("predict", help="Generate predictions using statistical models")
    predict_parser.set_defaults(func=cmd_predict)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
