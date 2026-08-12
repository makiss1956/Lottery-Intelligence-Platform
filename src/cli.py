"""
Command Line Interface (CLI) for the Lottery Intelligence Platform.

Provides a user-friendly terminal menu and command-line arguments to execute
data ingestion, statistical prediction, backtesting, and pipeline operations.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 65)
print(" LOTTERY INTELLIGENCE PLATFORM - STATISTICAL RESEARCH TOOL")
print(" Disclaimer: For educational & analytical research only.")
print(" Draws are independent random events. No prediction guarantees.")
print("=" * 65)

from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.core.logger import get_logger
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EuroJackpotImporter
from src.main import run_pipeline

logger = get_logger("CLI")

def cmd_predict(args):
    """Executes prediction mode and renders the statistical window."""
    db_mgr = DBManager()
    analyzer = FrequencyAnalyzer(db_mgr)
    predictor = ProbabilityPredictor(analyzer)

    candidates = predictor.predict_candidate_set(
        primary_count=args.primary, euro_count=args.euro
    )

    print("\n" + "=" * 50)
    print("🎯 LOTTERY INTELLIGENCE PLATFORM - PREDICTION")
    print("=" * 50)
    print(f"Primary Candidates ({args.primary} Numbers) : {candidates['primary_candidates']}")
    print(f"Euro Candidates ({args.euro} Numbers)     : {candidates['euro_candidates']}")
    print("=" * 50 + "\n")

def cmd_fetch(args):
    """Fetches and inserts the latest raw draw data into the database."""
    print("\n⏳ Fetching latest Eurojackpot draws...")
    
    db_mgr = DBManager()
    importer = EuroJackpotImporter(db_manager=db_mgr)
    draws = importer.fetch_latest_draws()
    
    inserted = 0
    for draw in draws:
        if db_mgr.insert_draw(draw):
            inserted += 1
    
    print(f"✅ Retrieved {len(draws)} draws. Inserted {inserted} new into database.\n")

def cmd_pipeline(args):
    """Executes the complete pipeline end-to-end."""
    print("\n🚀 Launching Full System Pipeline...\n")
    run_pipeline()

def main():
    parser = argparse.ArgumentParser(
        description="Lottery Intelligence Platform CLI - Statistical & Chaos Analysis Tools"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Pipeline command
    subparsers.add_parser("run", help="Run the complete end-to-end pipeline")

    # Predict command
    predict_parser = subparsers.add_parser(
        "predict", help="Generate the target statistical candidate set"
    )
    predict_parser.add_argument(
        "--primary", type=int, default=7, help="Number of primary candidate numbers (default: 7)"
    )
    predict_parser.add_argument(
        "--euro", type=int, default=3, help="Number of Euro candidate numbers (default: 3)"
    )

    # Fetch command
    subparsers.add_parser("fetch", help="Fetch latest draw data from source and save to DB")

    args = parser.parse_args()

    if args.command == "run":
        cmd_pipeline(args)
    elif args.command == "predict":
        cmd_predict(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    else:
        # Default behavior if no argument passed: run prediction
        cmd_predict(argparse.Namespace(primary=7, euro=3))

if __name__ == "__main__":
    main()
