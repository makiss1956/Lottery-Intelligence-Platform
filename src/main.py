"""
Main Eurojackpot pipeline.
Workflow:
1. Initialize database.
2. Synchronize historical CSV.
3. Retrieve the latest real draw from OPAP.
4. Store the latest draw.
5. Evaluate the previous prediction.
6. Determine the next draw.
7. Generate 3 main + 1 Joker prediction.
8. Save prediction.
9. Send email.
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("LotteryPipeline")

from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter


def run_pipeline() -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info("LOTTERY INTELLIGENCE PLATFORM")
    logger.info("PIPELINE START")
    logger.info("=" * 70)

    # ---------------------------------------------------------
    # STEP 1
    # ---------------------------------------------------------
    logger.info("STEP 1 - Initialize database")
    db = DBManager()
    logger.info("Database draws: %d", db.get_draw_count())

    # ---------------------------------------------------------
    # STEP 2
    # ---------------------------------------------------------
    logger.info("STEP 2 - Synchronize historical CSV")
    importer = EurojackpotImporter(db_manager=db)
    inserted = importer.sync_history()
    logger.info("CSV synchronization inserted %d draws", inserted)

    # ---------------------------------------------------------
    # STEP 3 — ΔΙΟΡΘΩΜΕΝΟ: Συνέχεια με τοπικά δεδομένα αν το API αποτύχει
    # ---------------------------------------------------------
    logger.info("STEP 3 - Retrieve latest live draw")
    latest_draw = importer.fetch_latest_draw()

    if latest_draw is None:
        logger.warning(
            "⚠ Δεν ήταν δυνατή η ανάκτηση κλήρωσης από το OPAP API. "
            "Συνεχίζουμε με την τελευταία αποθηκευμένη κλήρωση από τη βάση."
        )
        latest_draw = db.get_latest_draw()
        if latest_draw is None:
            raise RuntimeError(
                "Αποτυχία: Δεν υπάρχει καμία κλήρωση ούτε από το API ούτε από τη βάση."
            )
        logger.info(
            "✅ Χρήση τελευταίας αποθηκευμένης κλήρωσης: %s",
            latest_draw["draw_date"],
        )

    latest_date = latest_draw["draw_date"]
    logger.info(
        "LATEST DRAW: %s | Main=%s | Euro=%s",
        latest_date,
        latest_draw["primary_numbers"],
        latest_draw["euro_numbers"],
    )

    # ---------------------------------------------------------
    # STEP 4
    # ---------------------------------------------------------
    logger.info("STEP 4 - Evaluate previous prediction")
    predictions = db.get_predictions(limit=100)
    evaluated_prediction: Optional[Dict[str, Any]] = None
    previous_prediction: Optional[Dict[str, Any]] = None

    for prediction in predictions:
        if prediction.get("for_draw_date") != latest_date:
            continue
        previous_prediction = prediction
        evaluated_prediction = Backtester.evaluate_prediction(
            predicted_mains=prediction.get("predicted_primary", []),
            predicted_euros=prediction.get("predicted_euro", []),
            actual_draw=latest_draw,
        )
        logger.info("PREVIOUS PREDICTION RESULT")
        logger.info("Main hits: %d / 3", evaluated_prediction["main_hits_count"])
        logger.info("Joker hits: %d / 1", evaluated_prediction["euro_hits_count"])
        break

    if evaluated_prediction is None:
        logger.info("No previous prediction found for draw %s", latest_date)

    # ---------------------------------------------------------
    # STEP 5
    # ---------------------------------------------------------
    logger.info("STEP 5 - Determine next draw")
    next_draw_date = importer.get_next_draw_date()
    logger.info("NEXT DRAW TARGET: %s", next_draw_date)

    # ---------------------------------------------------------
    # STEP 6
    # ---------------------------------------------------------
    logger.info("STEP 6 - Statistical analysis")
    frequency_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = None

    # ---------------------------------------------------------
    # STEP 7
    # ---------------------------------------------------------
    logger.info("STEP 7 - Generate 3 + 1 prediction")
    predictor = ProbabilityPredictor(
        frequency_analyzer=frequency_analyzer,
        pattern_analyzer=pattern_analyzer,
    )
    prediction = predictor.predict_candidate_set(
        primary_count=3,
        euro_count=1,
    )
    primary_candidates = sorted(prediction["primary_candidates"])
    joker_candidates = sorted(prediction["euro_candidates"])

    if len(primary_candidates) != 3:
        raise RuntimeError(
            "Prediction must contain exactly 3 main numbers."
        )
    if len(joker_candidates) != 1:
        raise RuntimeError(
            "Prediction must contain exactly 1 Joker number."
        )

    logger.info("NEW PREDICTION: Main=%s | Joker=%s", primary_candidates, joker_candidates)

    # ---------------------------------------------------------
    # STEP 8
    # ---------------------------------------------------------
    logger.info("STEP 8 - Save prediction")
    if db.prediction_exists(next_draw_date):
        logger.warning("Prediction already exists for %s", next_draw_date)
        existing = next(
            (
                item for item in db.get_predictions(limit=100)
                if item.get("for_draw_date") == next_draw_date
            ),
            None,
        )
        return {
            "status": "already_exists",
            "latest_draw": latest_draw,
            "evaluated_prediction": evaluated_prediction,
            "next_draw_date": next_draw_date,
            "prediction": existing,
            "email_sent": False,
        }

    saved = db.save_prediction(
        for_draw_date=next_draw_date,
        primary_numbers=primary_candidates,
        euro_numbers=joker_candidates,
        metadata={
            "method": prediction.get("method", "composite_frequency_delay"),
        },
    )
    if not saved:
        raise RuntimeError("Prediction could not be saved.")
    logger.info("Prediction saved.")

    # ---------------------------------------------------------
    # STEP 9 - EMAIL
    # ---------------------------------------------------------
    logger.info("STEP 9 - Send email")
    email_sent = False
    try:
        from src.notifications.email_sender import LotteryEmailSender
        email_sender = LotteryEmailSender()
        email_prediction = {
            "for_draw_date": next_draw_date,
            "primary_candidates": primary_candidates,
            "euro_candidates": joker_candidates,
            "joker_candidates": joker_candidates,
            "method": prediction.get("method", "composite_frequency_delay"),
            "confidence": prediction.get("confidence", {}),
            "evaluation": evaluated_prediction,
        }
        email_sent = email_sender.send_prediction(
            prediction=email_prediction,
            stats={"total_draws": db.get_draw_count()},
        )
    except Exception:
        logger.exception("Email step failed.")

    # ---------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------
    result = {
        "status": "success",
        "latest_draw": latest_draw,
        "evaluated_prediction": evaluated_prediction,
        "next_draw_date": next_draw_date,
        "prediction": {
            "primary_candidates": primary_candidates,
            "joker": joker_candidates[0],
            "method": prediction.get("method", "composite_frequency_delay"),
        },
        "prediction_saved": True,
        "email_sent": email_sent,
        "new_draws_inserted": inserted,
        "total_draws": db.get_draw_count(),
    }

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETED")
    logger.info("Latest draw: %s", latest_date)
    logger.info("Next prediction: %s", next_draw_date)
    logger.info("Prediction: Main=%s | Joker=%s", primary_candidates, joker_candidates[0])
    logger.info("Previous prediction evaluated: %s", evaluated_prediction is not None)
    logger.info("Email sent: %s", email_sent)
    logger.info("=" * 70)

    return result


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception:
        logger.exception("PIPELINE FAILED.")
        sys.exit(1)
