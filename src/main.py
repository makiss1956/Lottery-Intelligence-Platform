"""
Main orchestration module for the Lottery Intelligence Platform.

Executes the complete pipeline: database setup, data fetching,
pattern analytics, probability prediction, and backtesting evaluation.
"""

from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.core.logger import get_logger
from src.database.database_manager import DatabaseManager
from src.importers.eurojackpot_importer import EuroJackpotImporter

logger = get_logger("MainPipeline")


def run_pipeline() -> None:
    """Executes full intelligence pipeline end-to-end."""
    logger.info("Starting Lottery Intelligence Platform pipeline...")

    # 1. Initialize Database
    db_mgr = DatabaseManager()
    db_mgr.initialize_database()

    # 2. Fetch Latest Draws
    importer = EuroJackpotImporter()
    draws = importer.fetch_latest_draws()
    logger.info(f"Retrieved {len(draws)} historical draw records.")

    # 3. Analyze Frequency & Structural Patterns
    freq_analyzer = FrequencyAnalyzer(db_mgr)
    pattern_analyzer = PatternAnalyzer(db_mgr)

    odd_even_dist = pattern_analyzer.analyze_odd_even_distribution()
    sum_stats = pattern_analyzer.analyze_sum_ranges()
    logger.info(f"Odd/Even distribution summary: {odd_even_dist}")
    logger.info(f"Sum range statistics: {sum_stats}")

    # 4. Generate Predictions with Integrated Pattern Filters
    predictor = ProbabilityPredictor(
        frequency_analyzer=freq_analyzer, pattern_analyzer=pattern_analyzer
    )
    candidates = predictor.predict_candidate_set(primary_count=7, euro_count=3)

    logger.info(f"Primary Candidates (7 Numbers): {candidates['primary_candidates']}")
    logger.info(f"Euro Candidates (3 Numbers)   : {candidates['euro_candidates']}")

    # 5. Run Backtesting Evaluations
    backtester = Backtester(db_mgr, predictor)
    eval_results = backtester.run_evaluations(eval_draws=10)
    logger.info(f"Backtest Evaluation Summary: {eval_results}")

    logger.info("Pipeline execution completed successfully.")


if __name__ == "__main__":
    run_pipeline()
