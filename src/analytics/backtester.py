"""
Prediction evaluation engine.
Evaluates:
- 3 predicted main numbers against 5 actual main numbers
- 1 predicted Joker/Euro number against 2 actual Euro numbers
"""
from typing import Any, Dict, List, Set
from src.core.logger import get_logger

logger = get_logger("Backtester")


class Backtester:
    @staticmethod
    def evaluate_prediction(
        predicted_mains: List[int],
        predicted_euros: List[int],
        actual_draw: Dict[str, Any],
    ) -> Dict[str, Any]:
        predicted_main_set: Set[int] = set(
            predicted_mains
        )
        predicted_joker_set: Set[int] = set(
            predicted_euros
        )
        actual_main_set: Set[int] = set(
            actual_draw.get(
                "primary_numbers",
                [],
            )
        )
        actual_euro_set: Set[int] = set(
            actual_draw.get(
                "euro_numbers",
                [],
            )
        )

        matched_mains = sorted(
            predicted_main_set
            .intersection(actual_main_set)
        )
        matched_jokers = sorted(
            predicted_joker_set
            .intersection(actual_euro_set)
        )

        main_hits = len(matched_mains)
        joker_hits = len(matched_jokers)

        logger.info(
            "Evaluation | Draw=%s | Main=%d/3 | Joker=%d/1",
            actual_draw.get("draw_date"),
            main_hits,
            joker_hits,
        )

        return {
            "draw_date": actual_draw.get("draw_date"),
            "main_hits_count": main_hits,
            "euro_hits_count": joker_hits,
            "joker_hits_count": joker_hits,
            "matched_main_numbers": matched_mains,
            "matched_euro_numbers": matched_jokers,
            "matched_joker": matched_jokers,
            "target_achieved": main_hits >= 3,
            "score_percentage": round(
                (main_hits / 3.0) * 100,
                2,
            ),
        }

    @staticmethod
    def run_batch_backtest(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Εκτελεί ομαδικό έλεγχο (backtest) σε λίστα αποτελεσμάτων.
        Υπολογίζει συνολικά στατιστικά επιτυχίας.
        """
        total = len(history)
        success_count = sum(
            1 for item in history
            if item.get("target_achieved", False)
        )
        total_hits = sum(
            item.get("main_hits_count", 0)
            for item in history
        )

        return {
            "total_draws": total,
            "success_count": success_count,
            "success_rate": (
                round(success_count / total * 100, 2)
                if total > 0 else 0.0
            ),
            "average_hits_per_draw": (
                round(total_hits / total, 2)
                if total > 0 else 0.0
            ),
            "history": history,
        }
