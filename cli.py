"""
Command Line Interface (CLI) for the Lottery Intelligence Platform.
"""

import argparse
import sys
from pathlib import Path

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
    db_mgr = DBManager()
    analyzer = FrequencyAnalyzer(db_mgr)
    predictor = ProbabilityPredictor(analyzer)
    candidates = predictor.predict_candidate_set(
        primary_count=args.primary, euro_count=args.euro
    )
    print("\n" + "=" * 50)
    print("🎯 PREDICTION")
    print(f"Primary Candidates ({args.primary}) : {candidates['primary_candidates']}")
    print(f"Euro Candidates ({args.euro})     : {candidates['euro_candidates']}")
    print("=" * 50 + "\n")

def cmd_fetch(args):
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
    print("\n🚀 Launching Full System Pipeline...\n")
    run_pipeline()

def main():
    parser = argparse.ArgumentParser(description="Lottery Intelligence Platform CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the complete end-to-end pipeline")

    predict_parser = subparsers.add_parser("predict", help="Generate candidate set")
    predict_parser.add_argument("--primary", type=int, default=7)
    predict_parser.add_argument("--euro", type=int, default=3)

    subparsers.add_parser("fetch", help="Fetch latest draws and save to DB")

    args = parser.parse_args()

    if args.command == "run":
        cmd_pipeline(args)
    elif args.command == "predict":
        cmd_predict(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    else:
        cmd_predict(argparse.Namespace(primary=7, euro=3))

if __name__ == "__main__":
    main()
