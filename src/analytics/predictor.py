"""
Probability Predictor and Number Selector for Lottery Intelligence Platform.

Applies weighted statistical models and pattern constraints to candidate numbers
to select an optimized set of 7 primary numbers and 3 Euro numbers.
"""

from typing import Any, Dict, List, Tuple

from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.core.logger import get_logger

logger = get_logger("ProbabilityPredictor")


class ProbabilityPredictor:
    """Combines statistical metrics to score and select optimal candidate numbers."""

    def __init__(self, analyzer: FrequencyAnalyzer):
        """Initialize predictor with a FrequencyAnalyzer instance.

        Args:
            analyzer (FrequencyAnalyzer): Populated frequency analyzer.
        """
        self.analyzer = analyzer

    def _score_main_numbers(
        self, freq_weight: float = 0.5, delay_weight: float = 0.5
    ) -> Dict[int, float]:
        """Calculates normalized statistical scores for main numbers (1-50).

        Args:
            freq_weight (float): Weight factor for frequency score.
            delay_weight (float): Weight factor for delay score.

        Returns:
            Dict[int, float]: Weighted scores for numbers 1 to 50.
        """
        report = self.analyzer.get_summary_report()
        freqs = report["main_frequencies"]
        delays = report["main_delays"]

        max_freq = max(freqs.values()) if freqs and max(freqs.values()) > 0 else 1
        max_delay = (
            max(delays.values()) if delays and max(delays.values()) > 0 else 1
        )

        scores: Dict[int, float] = {}
        for num in range(1, 51):
            norm_freq = freqs.get(num, 0) / max_freq
            norm_delay = delays.get(num, 0) / max_delay

            # Combined score equation
            scores[num] = (norm_freq * freq_weight) + (
                norm_delay * delay_weight
            )

        return scores

    def predict_candidate_set(
        self, primary_count: int = 7, euro_count: int = 3
    ) -> Dict[str, List[int]]:
        """Selects top candidate primary and Euro numbers based on probability scores.

        Args:
            primary_count (int): Number of main candidates to output (default: 7).
            euro_count (int): Number of Euro candidates to output (default: 3).

        Returns:
            Dict[str, List[int]]: Dictionary containing sorted candidate arrays.
        """
        scores = self._score_main_numbers()

        # Sort numbers by score descending
        sorted_mains = sorted(
            scores.keys(), key=lambda num: scores[num], reverse=True
        )
        selected_mains = sorted(sorted_mains[:primary_count])

        # Euro numbers selection based on frequency
        euro_freqs = self.analyzer.calculate_euro_frequencies()
        sorted_euros = sorted(
            euro_freqs.keys(), key=lambda num: euro_freqs[num], reverse=True
        )
        selected_euros = sorted(sorted_euros[:euro_count])

        logger.info(
            f"Generated prediction window: Main={selected_mains}, Euro={selected_euros}"
        )

        return {
            "primary_candidates": selected_mains,
            "euro_candidates": selected_euros,
        }
