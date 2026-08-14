import argparse
import sys
from src.database.db_manager import DBManager
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.importers.eurojackpot_importer import EurojackpotImporter
from src.core.logger import get_logger

logger = get_logger("CLI")

def cmd_fetch(args):
    logger.info("Fetching latest draw data...")
    importer = EurojackpotImporter()
    draws = importer.fetch_latest_draws()
    
    if not draws:
        logger.warning("No draws retrieved.")
        return

    db_mgr = DBManager()
    inserted = 0
    for draw in draws:
        if db_mgr.insert_draw(draw):
            inserted += 1

    logger.info(f"Fetch completed. Inserted {inserted} new draw(s).")

def cmd_predict(args):
    logger.info("Generating predictions...")
    db_mgr = DBManager()
    freq_analyzer = FrequencyAnalyzer(db_mgr)
    pattern_analyzer = PatternAnalyzer(db_mgr)
    
    # Ενεργοποίηση Composite Predictor με PatternAnalyzer
    predictor = ProbabilityPredictor(
        frequency_analyzer=freq_analyzer,
        pattern_analyzer=pattern_analyzer
    )

    prediction = predictor.predict_candidate_set(
        primary_count=args.primary,
        euro_count=args.euro
    )

    print("\n" + "="*50)
    print("🎯 EUROJACKPOT PREDICTION RESULTS")
    print("="*50)
    print(f"Primary Numbers ({len(prediction['primary_candidates'])}): {prediction['primary_candidates']}")
    print(f"Euro Numbers    ({len(prediction['euro_candidates'])}): {prediction['euro_candidates']}")
    print(f"Method Used     : {prediction.get('method', 'N/A')}")
    print("="*50 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Lottery Intelligence Platform CLI")
    subparsers = parser.add_parsers(dest="command", help="Available commands")

    # Command: fetch
    subparsers.add_parser("fetch", help="Fetch latest draw results from source")

    # Command: predict
    predict_parser = subparsers.add_parser("predict", help="Generate number predictions")
    predict_parser.add_argument("--primary", type=int, default=7, help="Number of primary candidates (default: 7)")
    predict_parser.add_argument("--euro", type=int, default=3, help="Number of Euro candidates (default: 3)")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "predict":
        cmd_predict(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
