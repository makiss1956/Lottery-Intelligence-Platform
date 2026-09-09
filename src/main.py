import sys
import logging
from datetime import datetime

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Main")

# --- Robust Imports ---
# 1. Importer Module
EurojackpotImporter = None
try:
    from importer.eurojackpot_importer import EurojackpotImporter
except ImportError:
    try:
        from importer import EurojackpotImporter
    except ImportError:
        try:
            from importer.csv_importer import EurojackpotImporter
        except ImportError:
            logger.error("Could not locate EurojackpotImporter class in importer package.")

# 2. Database Manager
try:
    from db_manager import DBManager
except ImportError:
    from database.db_manager import DBManager

# 3. Backtester
try:
    from backtester import Backtester
except ImportError:
    from backtest.backtester import Backtester

# 4. Analyzers
try:
    from analyzers import FrequencyAnalyzer, PatternAnalyzer
except ImportError:
    from analyzers.frequency import FrequencyAnalyzer
    from analyzers.pattern import PatternAnalyzer

# 5. Predictors
try:
    from predictors import ProbabilityPredictor
except ImportError:
    try:
        from predictors.probability_predictor import ProbabilityPredictor
    except ImportError:
        ProbabilityPredictor = None


def _ensure_count(pool, count, default_range):
    """Ensures a prediction pool has the required count of unique integers."""
    result = list(dict.fromkeys(pool))  # Deduplicate while preserving order
    for num in default_range:
        if len(result) >= count:
            break
        if num not in result:
            result.append(num)
    return sorted(result[:count])


def instantiate_predictor(db):
    """Dynamically instantiates ProbabilityPredictor matching its __init__ signature."""
    if ProbabilityPredictor is None:
        logger.warning("ProbabilityPredictor module not found. Skipping predictor step.")
        return None

    for attempt in [lambda: ProbabilityPredictor(db),
                    lambda: ProbabilityPredictor(db=db),
                    lambda: ProbabilityPredictor(db_manager=db),
                    lambda: ProbabilityPredictor()]:
        try:
            return attempt()
        except TypeError:
            continue

    logger.error("Failed to match ProbabilityPredictor initialization signature.")
    return None


def run_pipeline():
    logger.info("==================================================")
    logger.info("STARTING LOTTERY INTELLIGENCE PIPELINE")
    logger.info("==================================================")

    if EurojackpotImporter is None:
        raise ImportError("EurojackpotImporter could not be imported from src/importer.")

    # 1. Initialize Database & Importer
    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)

    # 2. Synchronize CSV History
    logger.info("STEP 1: Synchronizing history from CSV...")
    importer.sync_history()

    # 3. Fetch Latest Draw
    logger.info("STEP 2: Fetching latest draw...")
    latest_draw = importer.get_latest_draw()
    latest_date = latest_draw.get("draw_date") if latest_draw else None

    # 4. Validate Previous Predictions
    logger.info("STEP 3: Validating previous draw performance...")
    if latest_date:
        backtester = Backtester(db_manager=db)
        backtester.evaluate_draw(latest_date)

    # 5. Compute Next Target Date
    target_date = importer.get_next_draw_date()
    logger.info(f"STEP 4: Target draw date set to {target_date}")

    # 6. Run Ensemble Prediction Engines
    logger.info("STEP 5: Generating Hybrid Ensemble predictions...")

    freq_analyzer = FrequencyAnalyzer(db_manager=db)
    freq_primary, freq_euro = freq_analyzer.analyze()

    pattern_analyzer = PatternAnalyzer(db_manager=db)
    pattern_primary, pattern_euro = pattern_analyzer.analyze()

    prob_predictor = instantiate_predictor(db)
    if prob_predictor and hasattr(prob_predictor, "predict"):
        prob_primary, prob_euro = prob_predictor.predict()
    else:
        prob_primary, prob_euro = [], []

    # 7. Aggregate & Backfill Pools
    combined_primary = freq_primary + pattern_primary + prob_primary
    combined_euro = freq_euro + pattern_euro + prob_euro

    final_primary = _ensure_count(combined_primary, 5, range(1, 51))
    final_euro = _ensure_count(combined_euro, 2, range(1, 13))

    logger.info(f"FINAL ENSEMBLE PREDICTION for {target_date}:")
    logger.info(f"  Primary Numbers (5/50): {final_primary}")
    logger.info(f"  Euro Numbers    (2/12): {final_euro}")

    # 8. Save Prediction to Database
    db.save_prediction(
        for_draw_date=target_date,
        primary_numbers=final_primary,
        euro_numbers=final_euro,
        metadata={
            "generated_at": datetime.utcnow().isoformat(),
            "models_used": ["Frequency", "Pattern", "Probability"]
        }
    )

    logger.info("PIPELINE EXECUTION COMPLETE")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.critical(f"Pipeline failed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
