"""
Backtesting and Evaluation Engine for Lottery Intelligence Platform.

Compares predicted candidate sets against actual draw results to measure
model accuracy, calculate hit ratios, and maintain evaluation logs.
"""

from typing import Any, Dict, List, Set

from src.core.logger import get_logger

logger = get_logger("Backtester")


class Backtester:
    """Evaluates prediction models against historic or new draw outcomes."""

    @staticmethod
    def evaluate_prediction(
        predicted_mains: List[int],
        predicted_euros: List[int],
        actual_draw: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compares predicted number set with actual draw result.

        Args:
            predicted_mains (List[int]): List of predicted primary candidate numbers.
            predicted_euros (List[int]): List of predicted Euro numbers.
            actual_draw (Dict[str, Any]): Actual draw record with 'numbers' and 'euro_numbers'.

        Returns:
            Dict[str, Any]: Performance evaluation metrics and match details.
        """
        actual_mains_set: Set[int] = set(actual_draw.get("numbers", []))
        actual_euros_set: Set[int] = set(actual_draw.get("euro_numbers", []))

        matched_mains = sorted(list(set(predicted_mains).intersection(actual_mains_set)))
        matched_euros = sorted(list(set(predicted_euros).intersection(actual_euros_set)))

        main_hit_count = len(matched_mains)
        euro_hit_count = len(matched_euros)

        # Target threshold condition: At least 3 main hits out of candidate set
        target_met = main_hit_count >= 3

        logger.info(
            f"Evaluation for draw {actual_draw.get('draw_date')}: "
            f"Main Hits = {main_hit_count}/5 (Matched: {matched_mains}), "
            f"Euro Hits = {euro_hit_count}/2 (Matched: {matched_euros})"
        )

        return {
            "draw_date": actual_draw.get("draw_date"),
            "main_hits_count": main_hit_count,
            "euro_hits_count": euro_hit_count,
            "matched_main_numbers": matched_mains,
            "matched_euro_numbers": matched_euros,
            "target_achieved": target_met,
            "score_percentage": round((main_hit_count / 5.0) * 100, 2),
        }

    @staticmethod
    def run_batch_backtest(
        prediction_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregates multiple evaluation results to assess model stability over time.

        Args:
            prediction_history (List[Dict[str, Any]]): List of evaluation reports.

        Returns:
            Dict[str, Any]: Cumulative performance statistics.
        """
        if not prediction_history:
            return {"total_tests": 0, "success_rate": 0.0, "average_hits": 0.0}

        total_tests = len(prediction_history)
        successful_runs = sum(
            1 for res in prediction_history if res.get("target_achieved", False)
        )
        total_hits = sum(res.get("main_hits_count", 0) for res in prediction_history)

        avg_hits = total_hits / total_tests
        success_rate = (successful_runs / total_tests) * 100

        logger.info(
            f"Batch Backtest Completed: Tests={total_tests}, "
            f"Success Rate (>=3 hits)={success_rate:.2f}%, Avg Hits={avg_hits:.2f}"
        )

        return {
            "total_tests": total_tests,
            "successful_targets": successful_runs,
            "success_rate_percentage": round(success_rate, 2),
            "average_main_hits": round(avg_hits, 2),
        }
