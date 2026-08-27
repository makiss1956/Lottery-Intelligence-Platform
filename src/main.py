"""
Main Execution Pipeline for Lottery Intelligence Platform.

Pipeline:

1. Synchronize CSV history with database.
2. Detect whether a new draw was added.
3. Validate the prediction assigned to that draw.
4. Generate exactly one prediction for the next draw.
5. Send exactly one email for the new prediction.
6. Generate dashboard.
"""

import sys
from datetime import datetime

from src.core.logger import get_logger
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor


logger = get_logger("Main")


def run_pipeline() -> None:
    """Execute the complete lottery intelligence pipeline."""

    logger.info(
        "=================================================="
    )
    logger.info(
        "STARTING LOTTERY INTELLIGENCE PIPELINE"
    )
    logger.info(
        "=================================================="
    )

    db = DBManager()

    importer = EurojackpotImporter(
        db_manager=db
    )

    # -------------------------------------------------
    # STEP 1
    # Synchronize CSV with database
    # -------------------------------------------------

    logger.info(
        "STEP 1: Synchronizing CSV history..."
    )

    inserted_count = importer.sync_history()

    logger.info(
        "CSV synchronization inserted %d new draws.",
        inserted_count,
    )

    # -------------------------------------------------
    # STEP 2
    # Detect latest draw
    # -------------------------------------------------

    all_draws = db.get_all_draws()

    if not all_draws:
        logger.error(
            "CRITICAL: Database contains no draws."
        )
        sys.exit(1)

    latest_draw = all_draws[0]

    logger.info(
        "Latest database draw: %s | "
        "Primary=%s | Euro=%s",
        latest_draw["draw_date"],
        latest_draw["primary_numbers"],
        latest_draw["euro_numbers"],
    )

    # -------------------------------------------------
    # STEP 3
    # If there is no new draw, STOP.
    #
    # This prevents duplicate predictions and emails.
    # -------------------------------------------------

    if inserted_count == 0:
        logger.info(
            "No new draw detected."
        )

        logger.info(
            "No validation required."
        )

        logger.info(
            "No new prediction will be generated."
        )

        logger.info(
            "No email will be sent."
        )

        logger.info(
            "PIPELINE STOPPED SAFELY."
        )

        return

    # -------------------------------------------------
    # STEP 4
    # Validate prediction for the new draw
    # -------------------------------------------------

    logger.info(
        "STEP 2: Validating previous prediction..."
    )

    validation_result = (
        db.validate_prediction_for_draw(
            latest_draw
        )
    )

    if validation_result:
        logger.info(
            "=============================================="
        )

        logger.info(
            "PREDICTION VALIDATION"
        )

        logger.info(
            "Draw: %s",
            latest_draw["draw_date"],
        )

        logger.info(
            "Predicted primary: %s",
            validation_result.get(
                "predicted_primary"
            ),
        )

        logger.info(
            "Actual primary: %s",
            latest_draw["primary_numbers"],
        )

        logger.info(
            "Main hits: %d/5",
            validation_result[
                "main_hits_count"
            ],
        )

        logger.info(
            "Matched main numbers: %s",
            validation_result[
                "matched_main_numbers"
            ],
        )

        logger.info(
            "Predicted Euro: %s",
            validation_result.get(
                "predicted_euro"
            ),
        )

        logger.info(
            "Actual Euro: %s",
            latest_draw["euro_numbers"],
        )

        logger.info(
            "Euro hits: %d/2",
            validation_result[
                "euro_hits_count"
            ],
        )

        logger.info(
            "Matched Euro numbers: %s",
            validation_result[
                "matched_euro_numbers"
            ],
        )

        logger.info(
            "Target >=3 main numbers: %s",
            "YES"
            if validation_result[
                "target_achieved"
            ]
            else "NO",
        )

        logger.info(
            "Score: %.2f%%",
            validation_result[
                "score_percentage"
            ],
        )

        logger.info(
            "=============================================="
        )

    else:
        logger.warning(
            "No stored prediction exists for draw %s.",
            latest_draw["draw_date"],
        )

    # -------------------------------------------------
    # STEP 5
    # Determine next draw
    # -------------------------------------------------

    next_draw_date = (
        importer.get_next_draw_date()
    )

    logger.info(
        "STEP 3: Next draw date = %s",
        next_draw_date,
    )

    # -------------------------------------------------
    # STEP 6
    # Safety check against duplicate prediction
    # -------------------------------------------------

    if db.prediction_exists(
        next_draw_date
    ):
        logger.warning(
            "Prediction already exists for %s.",
            next_draw_date,
        )

        logger.warning(
            "NO duplicate prediction will be generated."
        )

        logger.warning(
            "NO duplicate email will be sent."
        )

        return

    # -------------------------------------------------
    # STEP 7
    # Generate new prediction
    # -------------------------------------------------

    logger.info(
        "STEP 4: Generating prediction..."
    )

    freq_analyzer = FrequencyAnalyzer(db)

    pattern_analyzer = PatternAnalyzer(db)

    predictor = ProbabilityPredictor(
        freq_analyzer,
        pattern_analyzer,
    )

    prediction = predictor.predict_candidate_set(
        primary_count=7,
        euro_count=3,
    )

    primary_candidates = prediction.get(
        "primary_candidates",
        [],
    )

    euro_candidates = prediction.get(
        "euro_candidates",
        [],
    )

    if len(primary_candidates) != 7:
        logger.error(
            "Predictor did not return exactly 7 "
            "primary candidates."
        )
        sys.exit(1)

    if len(euro_candidates) != 3:
        logger.error(
            "Predictor did not return exactly 3 "
            "Euro candidates."
        )
        sys.exit(1)

    logger.info(
        "Prediction generated:"
    )

    logger.info(
        "Primary 7: %s",
        primary_candidates,
    )

    logger.info(
        "Euro 3: %s",
        euro_candidates,
    )

    # -------------------------------------------------
    # STEP 8
    # Save prediction
    # -------------------------------------------------

    prediction_record = {
        "prediction_date": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "for_draw_date": next_draw_date,
        "predicted_primary": primary_candidates,
        "predicted_euro": euro_candidates,
        "method": prediction.get(
            "method",
            "composite_freq_delay",
        ),
        "confidence": prediction.get(
            "confidence",
            {},
        ),
    }

    prediction_saved = db.insert_prediction(
        prediction_record
    )

    if not prediction_saved:
        logger.warning(
            "Prediction was NOT inserted."
        )

        logger.warning(
            "Email will NOT be sent."
        )

        return

    logger.info(
        "Prediction successfully saved for %s.",
        next_draw_date,
    )

    # -------------------------------------------------
    # STEP 9
    # Send exactly one email
    # -------------------------------------------------

    logger.info(
        "STEP 5: Sending prediction email..."
    )

    try:
        from src.notifications.email_sender import (
            LotteryEmailSender
        )

        sender = LotteryEmailSender()

        stats = {
            "total_draws": len(all_draws),
            "latest_draw": latest_draw,
            "validation": validation_result,
        }

        sender.send_prediction(
            {
                "prediction_for_date": next_draw_date,
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
            stats,
        )

        logger.info(
            "Prediction email sent successfully."
        )

    except Exception as exc:
        logger.error(
            "Email sending failed: %s",
            exc,
        )

    # -------------------------------------------------
    # STEP 10
    # Dashboard
    # -------------------------------------------------

    logger.info(
        "STEP 6: Generating dashboard..."
    )

    try:
        from src.analytics.dashboard import (
            SuccessDashboard
        )

        dashboard = SuccessDashboard(db)

        dashboard.generate_html_report()

        logger.info(
            "Dashboard generated successfully."
        )

    except Exception as exc:
        logger.warning(
            "Dashboard generation failed: %s",
            exc,
        )

    # -------------------------------------------------
    # COMPLETE
    # -------------------------------------------------

    logger.info(
        "=================================================="
    )

    logger.info(
        "LOTTERY INTELLIGENCE PIPELINE COMPLETED"
    )

    logger.info(
        "New draws inserted: %d",
        inserted_count,
    )

    logger.info(
        "Validation performed: %s",
        "YES" if validation_result else "NO",
    )

    logger.info(
        "New prediction created: YES"
    )

    logger.info(
        "=================================================="
    )


if __name__ == "__main__":
    run_pipeline()
