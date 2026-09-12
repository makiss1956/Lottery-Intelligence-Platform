"""
Main execution pipeline for the Lottery Intelligence Platform.

Pipeline:
1. Synchronize historical data.
2. Retrieve the latest real draw.
3. Evaluate the previous prediction against that draw.
4. Determine the next draw date.
5. Analyze historical data.
6. Generate 7 main + 3 Euro candidates.
7. Save the prediction.
8. Send the prediction email.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ----------------------------------------------------------------------
# Project paths
# ----------------------------------------------------------------------

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent

for path_entry in (str(ROOT_DIR), str(SRC_DIR)):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("LotteryPipeline")


# ----------------------------------------------------------------------
# Project imports
# ----------------------------------------------------------------------

from src.analytics.backtester import Backtester
from src.analytics.predictor import ProbabilityPredictor
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter


# ----------------------------------------------------------------------
# Optional analysis modules
# ----------------------------------------------------------------------

try:
    from src.analytics.frequency_analyzer import FrequencyAnalyzer
except ImportError as exc:
    FrequencyAnalyzer = None
    FREQUENCY_IMPORT_ERROR = exc


try:
    from src.analytics.pattern_analyzer import PatternAnalyzer
except ImportError as exc:
    PatternAnalyzer = None
    PATTERN_IMPORT_ERROR = exc


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _extract_numbers(
    prediction: Dict[str, Any],
    primary_count: int = 7,
    euro_count: int = 3,
) -> tuple[List[int], List[int]]:
    """
    Extract and strictly validate the 7 main + 3 Euro prediction.

    No silent padding with arbitrary numbers is performed here.
    The predictor must actually return the requested number of
    candidates.
    """
    primary = prediction.get("primary_candidates", [])
    euro = prediction.get("euro_candidates", [])

    if not isinstance(primary, list):
        raise RuntimeError(
            "Predictor returned invalid primary_candidates."
        )

    if not isinstance(euro, list):
        raise RuntimeError(
            "Predictor returned invalid euro_candidates."
        )

    primary = [int(number) for number in primary]
    euro = [int(number) for number in euro]

    primary = sorted(set(primary))
    euro = sorted(set(euro))

    if len(primary) != primary_count:
        raise RuntimeError(
            f"Predictor returned {len(primary)} main candidates. "
            f"Expected exactly {primary_count}."
        )

    if len(euro) != euro_count:
        raise RuntimeError(
            f"Predictor returned {len(euro)} Euro candidates. "
            f"Expected exactly {euro_count}."
        )

    if not all(1 <= number <= 50 for number in primary):
        raise RuntimeError(
            f"Invalid main prediction numbers: {primary}"
        )

    if not all(1 <= number <= 12 for number in euro):
        raise RuntimeError(
            f"Invalid Euro prediction numbers: {euro}"
        )

    return primary, euro


def _run_frequency_analysis(
    db_manager: DBManager,
) -> Any:
    """Create and run the frequency analyzer."""
    if FrequencyAnalyzer is None:
        raise RuntimeError(
            "FrequencyAnalyzer could not be imported: "
            f"{FREQUENCY_IMPORT_ERROR}"
        )

    analyzer = FrequencyAnalyzer(db_manager=db_manager)

    if not hasattr(analyzer, "analyze"):
        raise RuntimeError(
            "FrequencyAnalyzer does not provide the required "
            "analyze() method."
        )

    result = analyzer.analyze()

    logger.info("Frequency analysis completed.")

    return analyzer


def _run_pattern_analysis(
    db_manager: DBManager,
) -> Any:
    """Create and run the pattern analyzer."""
    if PatternAnalyzer is None:
        logger.warning(
            "PatternAnalyzer is not available. "
            "Continuing without pattern analysis."
        )
        return None

    analyzer = PatternAnalyzer(db_manager=db_manager)

    if hasattr(analyzer, "analyze"):
        analyzer.analyze()
        logger.info("Pattern analysis completed.")

    return analyzer


# ----------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------

def run_pipeline() -> Dict[str, Any]:
    """Run the complete Eurojackpot pipeline."""

    logger.info("=" * 70)
    logger.info("LOTTERY INTELLIGENCE PLATFORM - PIPELINE START")
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # STEP 1 - Database
    # ------------------------------------------------------------------

    logger.info("STEP 1/8: Initializing database.")

    db_manager = DBManager()

    logger.info(
        "Database initialized. Current draw count: %d",
        db_manager.get_draw_count(),
    )

    # ------------------------------------------------------------------
    # STEP 2 - Synchronize history
    # ------------------------------------------------------------------

    logger.info("STEP 2/8: Synchronizing draw history.")

    importer = EurojackpotImporter(
        db_manager=db_manager,
    )

    inserted_count = importer.sync_history()

    logger.info(
        "History synchronization completed. New draws: %d",
        inserted_count,
    )

    # ------------------------------------------------------------------
    # STEP 3 - Get latest real draw
    # ------------------------------------------------------------------

    logger.info("STEP 3/8: Retrieving latest real draw.")

    latest_draw = importer.get_latest_draw()

    if latest_draw is None:
        raise RuntimeError(
            "No latest Eurojackpot draw could be retrieved."
        )

    latest_date = latest_draw["draw_date"]

    logger.info(
        "Latest draw: %s | Main=%s | Euro=%s",
        latest_date,
        latest_draw["primary_numbers"],
        latest_draw["euro_numbers"],
    )

    # Make absolutely sure the latest draw is in SQLite.
    stored_latest = db_manager.get_draw(latest_date)

    if stored_latest is None:
        raise RuntimeError(
            f"Latest draw {latest_date} was retrieved but was not "
            "stored in SQLite."
        )

    # ------------------------------------------------------------------
    # STEP 4 - Evaluate previous prediction
    # ------------------------------------------------------------------

    logger.info("STEP 4/8: Evaluating previous prediction.")

    predictions = db_manager.get_predictions(limit=20)

    evaluated_prediction: Optional[Dict[str, Any]] = None

    for prediction in predictions:
        target_date = prediction.get("for_draw_date")

        if target_date != latest_date:
            continue

        predicted_primary = prediction.get(
            "predicted_primary",
            [],
        )

        predicted_euro = prediction.get(
            "predicted_euro",
            [],
        )

        evaluated_prediction = Backtester.evaluate_prediction(
            predicted_mains=predicted_primary,
            predicted_euros=predicted_euro,
            actual_draw=latest_draw,
        )

        logger.info(
            "Previous prediction evaluation: "
            "main hits=%d, Euro hits=%d, target=%s",
            evaluated_prediction["main_hits_count"],
            evaluated_prediction["euro_hits_count"],
            evaluated_prediction["target_achieved"],
        )

        break

    if evaluated_prediction is None:
        logger.info(
            "No stored prediction was found for draw %s.",
            latest_date,
        )

    # ------------------------------------------------------------------
    # STEP 5 - Determine next draw
    # ------------------------------------------------------------------

    logger.info("STEP 5/8: Determining next draw date.")

    next_draw_date = importer.get_next_draw_date()

    if not next_draw_date:
        raise RuntimeError(
            "Importer returned an empty next draw date."
        )

    logger.info(
        "Next prediction target: %s",
        next_draw_date,
    )

    # Prevent duplicate predictions for the same target draw.
    if db_manager.prediction_exists(next_draw_date):
        logger.warning(
            "A prediction already exists for draw %s.",
            next_draw_date,
        )

        existing_predictions = db_manager.get_predictions(limit=20)

        existing = next(
            (
                prediction
                for prediction in existing_predictions
                if prediction.get("for_draw_date") == next_draw_date
            ),
            None,
        )

        return {
            "status": "already_exists",
            "latest_draw": latest_draw,
            "evaluated_prediction": evaluated_prediction,
            "next_draw_date": next_draw_date,
            "prediction": existing,
        }

    # ------------------------------------------------------------------
    # STEP 6 - Analyze historical data
    # ------------------------------------------------------------------

    logger.info("STEP 6/8: Running historical analysis.")

    frequency_analyzer = _run_frequency_analysis(
        db_manager,
    )

    pattern_analyzer = _run_pattern_analysis(
        db_manager,
    )

    # ------------------------------------------------------------------
    # STEP 7 - Generate 7 + 3 prediction
    # ------------------------------------------------------------------

    logger.info(
        "STEP 7/8: Generating prediction with exactly "
        "7 main + 3 Euro candidates."
    )

    predictor = ProbabilityPredictor(
        frequency_analyzer=frequency_analyzer,
        pattern_analyzer=pattern_analyzer,
    )

    prediction = predictor.predict_candidate_set(
        primary_count=7,
        euro_count=3,
    )

    primary_candidates, euro_candidates = _extract_numbers(
        prediction,
        primary_count=7,
        euro_count=3,
    )

    logger.info(
        "Prediction generated: Main=%s | Euro=%s",
        primary_candidates,
        euro_candidates,
    )

    # ------------------------------------------------------------------
    # STEP 8 - Save and email prediction
    # ------------------------------------------------------------------

    logger.info("STEP 8/8: Saving prediction and sending email.")

    metadata = {
        "method": prediction.get(
            "method",
            "composite_freq_delay",
        ),
        "confidence": prediction.get(
            "confidence",
            {},
        ),
        "primary_scores": prediction.get(
            "primary_scores",
            {},
        ),
        "euro_scores": prediction.get(
            "euro_scores",
            {},
        ),
    }

    saved = db_manager.save_prediction(
        for_draw_date=next_draw_date,
        primary_numbers=primary_candidates,
        euro_numbers=euro_candidates,
        metadata=metadata,
    )

    if not saved:
        raise RuntimeError(
            f"Prediction for draw {next_draw_date} could not be saved."
        )

    logger.info(
        "Prediction saved successfully for draw %s.",
        next_draw_date,
    )

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    email_sent = False

    try:
        from src.notifications.email_sender import LotteryEmailSender

        email_sender = LotteryEmailSender()

        # The sender API may expose different public methods depending
        # on the existing project implementation. We deliberately use
        # only the supported send_prediction method here.
        if hasattr(email_sender, "send_prediction"):
            email_result = email_sender.send_prediction(
                prediction={
                    "for_draw_date": next_draw_date,
                    "primary_candidates": primary_candidates,
                    "euro_candidates": euro_candidates,
                    "method": prediction.get(
                        "method",
                        "composite_freq_delay",
                    ),
                    "confidence": prediction.get(
                        "confidence",
                        {},
                    ),
                }
            )

            email_sent = bool(email_result)

        else:
            logger.warning(
                "LotteryEmailSender does not provide "
                "send_prediction(). Prediction was saved, "
                "but email was not sent."
            )

    except Exception:
        logger.exception(
            "Prediction was saved, but email sending failed."
        )

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------

    result = {
        "status": "success",
        "latest_draw": latest_draw,
        "evaluated_prediction": evaluated_prediction,
        "next_draw_date": next_draw_date,
        "prediction": {
            "primary_candidates": primary_candidates,
            "euro_candidates": euro_candidates,
            "method": prediction.get(
                "method",
                "composite_freq_delay",
            ),
            "confidence": prediction.get(
                "confidence",
                {},
            ),
        },
        "prediction_saved": True,
        "email_sent": email_sent,
        "new_draws_inserted": inserted_count,
        "total_draws": db_manager.get_draw_count(),
    }

    logger.info("=" * 70)
    logger.info("LOTTERY INTELLIGENCE PLATFORM - PIPELINE COMPLETED")
    logger.info(
        "Latest draw: %s",
        latest_date,
    )
    logger.info(
        "Next draw: %s",
        next_draw_date,
    )
    logger.info(
        "Prediction: Main=%s | Euro=%s",
        primary_candidates,
        euro_candidates,
    )
    logger.info(
        "Email sent: %s",
        email_sent,
    )
    logger.info("=" * 70)

    return result


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    try:
        run_pipeline()

    except Exception:
        logger.exception(
            "PIPELINE FAILED."
        )
        sys.exit(1)
