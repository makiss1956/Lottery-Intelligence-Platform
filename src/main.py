import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root directory is in sys.path for proper module resolution
SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent

for path_entry in (str(SRC_DIR), str(ROOT_DIR)):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Main")

# Internal module imports with absolute/relative fallbacks
try:
    from src.database.db_manager import DBManager
except ImportError:
    from db_manager import DBManager

try:
    from src.analytics.backtester import Backtester
except ImportError:
    try:
        from backtester import Backtester
    except ImportError:
        Backtester = None

# Import Analyzers
try:
    from src.analytics.frequency_analyzer import FrequencyAnalyzer
    from src.analytics.pattern_analyzer import PatternAnalyzer
except ImportError:
    try:
        from src.analytics.analyzers import FrequencyAnalyzer, PatternAnalyzer
    except ImportError:
        try:
            from analyzers import FrequencyAnalyzer, PatternAnalyzer
        except ImportError:
            FrequencyAnalyzer, PatternAnalyzer = None, None

# Importer / Fetcher with Safe Fallback
EurojackpotImporter = None
for import_stmt in [
    "from src.importer import EurojackpotImporter",
    "from src.fetchers.opap_fetcher import OPAPFetcher as EurojackpotImporter",
    "from src.importer.opap_fetcher import OPAPFetcher as EurojackpotImporter",
    "from src.importer.eurojackpot_importer import EurojackpotImporter",
    "from opap_fetcher import OPAPFetcher as EurojackpotImporter",
    "from eurojackpot_importer import EurojackpotImporter",
]:
    try:
        exec(import_stmt)
        if EurojackpotImporter is not None:
            break
    except Exception:
        continue

# Fallback Importer class if no module was found
if EurojackpotImporter is None:
    class DummyImporter:
        def __init__(self, db_manager=None):
            self.db = db_manager
        def sync_history(self):
            logger.info("Importer module not found; skipping CSV sync.")
        def get_latest_draw(self):
            if self.db:
                draws = self.db.get_all_draws()
                return draws[-1] if draws else None
            return None
        def get_next_draw_date(self):
            return (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    EurojackpotImporter = DummyImporter

# Predictor imports
ProbabilityPredictor = None
for import_stmt in [
    "from src.predictors.probability_predictor import ProbabilityPredictor",
    "from src.analytics.predictor import Predictor as ProbabilityPredictor",
    "from predictors import ProbabilityPredictor",
    "from predictor import Predictor as ProbabilityPredictor",
]:
    try:
        exec(import_stmt)
        if ProbabilityPredictor is not None:
            break
    except Exception:
        continue


def _ensure_count(pool, count, default_range):
    """Ensures a prediction pool has the required count of unique integers."""
    result = list(dict.fromkeys(pool))  # Deduplicate while preserving order
    for num in default_range:
        if len(result) >= count:
            break
        if num not in result:
            result.append(num)
    return sorted(result[:count])


def run_pipeline():
    logger.info("==================================================")
    logger.info("STARTING LOTTERY INTELLIGENCE PIPELINE")
    logger.info("==================================================")

    # 1. Initialize Database & Importer
    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)

    # 2. Synchronize CSV History
    logger.info("STEP 1: Synchronizing history...")
    if hasattr(importer, "sync_history"):
        importer.sync_history()

    # 3. Fetch Latest Draw
    logger.info("STEP 2: Fetching latest draw...")
    latest_draw = importer.get_latest_draw() if hasattr(importer, "get_latest_draw") else None
    latest_date = latest_draw.get("draw_date") if (latest_draw and isinstance(latest_draw, dict)) else None

    # 4. Validate Previous Predictions
    logger.info("STEP 3: Validating previous draw performance...")
    if latest_date and Backtester:
        try:
            backtester = Backtester(db_manager=db)
            if hasattr(backtester, "evaluate_draw"):
                backtester.evaluate_draw(latest_date)
        except Exception as e:
            logger.warning(f"Backtesting skipped: {e}")

    # 5. Compute Next Target Date
    target_date = importer.get_next_draw_date() if hasattr(importer, "get_next_draw_date") else (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    logger.info(f"STEP 4: Target draw date set to {target_date}")

    # 6. Run Ensemble Prediction Engines
    logger.info("STEP 5: Generating Hybrid Ensemble predictions...")

    freq_primary, freq_euro = [], []
    if FrequencyAnalyzer:
        try:
            freq_analyzer = FrequencyAnalyzer(db_manager=db)
            freq_primary, freq_euro = freq_analyzer.analyze()
        except Exception as e:
            logger.warning(f"FrequencyAnalyzer failed: {e}")

    pattern_primary, pattern_euro = [], []
    if PatternAnalyzer:
        try:
            pattern_analyzer = PatternAnalyzer(db_manager=db)
            pattern_primary, pattern_euro = pattern_analyzer.analyze()
        except Exception as e:
            logger.warning(f"PatternAnalyzer failed: {e}")

    prob_primary, prob_euro = [], []
    if ProbabilityPredictor:
        try:
            try:
                predictor = ProbabilityPredictor(db)
            except TypeError:
                predictor = ProbabilityPredictor(db_manager=db)
            prob_primary, prob_euro = predictor.predict()
        except Exception as e:
            logger.warning(f"ProbabilityPredictor failed: {e}")

    # 7. Aggregate & Backfill Pools
    combined_primary = freq_primary + pattern_primary + prob_primary
    combined_euro = freq_euro + pattern_euro + prob_euro

    final_primary = _ensure_count(combined_primary, 5, range(1, 51))
    final_euro = _ensure_count(combined_euro, 2, range(1, 13))

    logger.info(f"FINAL ENSEMBLE PREDICTION for {target_date}:")
    logger.info(f"  Primary Numbers (5/50): {final_primary}")
    logger.info(f"  Euro Numbers    (2/12): {final_euro}")

    # 8. Save Prediction to Database
    if hasattr(db, "save_prediction"):
        db.save_prediction(
            for_draw_date=target_date,
            primary_numbers=final_primary,
            euro_numbers=final_euro,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "models_used": ["Frequency", "Pattern", "Probability"]
            }
        )
    elif hasattr(db, "insert_prediction"):
        db.insert_prediction({
            "prediction_date": datetime.now().strftime("%Y-%m-%d"),
            "for_draw_date": target_date,
            "model_name": "Hybrid Ensemble",
            "predicted_primary": final_primary,
            "predicted_euro": final_euro
        })

    logger.info("PIPELINE EXECUTION COMPLETE")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.critical(f"Pipeline failed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
