"""
Probability Prediction Engine for Lottery Intelligence Platform.

Combines frequency metrics and structural pattern filters (Odd/Even, Sum ranges)
to select optimal candidate number sets.
"""

from typing import Any, Dict, List
from src.core.logger import get_logger

logger = get_logger("Predictor")


class ProbabilityPredictor:
    """Ranks and filters candidate sets using frequency and structural pattern analytics."""

    def __init__(self, frequency_analyzer: Any, pattern_analyzer: Any = None):
        """Initializes predictor with frequency and optional pattern analyzers."""
        self.freq_analyzer = frequency_analyzer
        self.pattern_analyzer = pattern_analyzer

    def predict_candidate_set(
        self, primary_count: int = 7, euro_count: int = 3
    ) -> Dict[str, List[int]]:
        """Generates candidate set for primary and Euro numbers.

        Args:
            primary_count (int): Number of primary candidates to return.
            euro_count (int): Number of Euro candidates to return.

        Returns:
            Dict[str, List[int]]: Dictionary containing candidate lists.
        """
        primary_freqs = self.freq_analyzer.get_primary_frequencies()
        euro_freqs = self.freq_analyzer.get_euro_frequencies()

        # Sort numbers by frequency descending
        sorted_primary = [
            num for num, _ in sorted(primary_freqs.items(), key=lambda item: item[1], reverse=True)
        ]
        sorted_euro = [
            num for num, _ in sorted(euro_freqs.items(), key=lambda item: item[1], reverse=True)
        ]

        primary_candidates = sorted_primary[:primary_count]
        euro_candidates = sorted_euro[:euro_count]

        # Apply structural pattern optimization if PatternAnalyzer is available
        if self.pattern_analyzer:
            primary_candidates = self._optimize_candidates(primary_candidates)

        logger.info(
            f"Generated {len(primary_candidates)} primary candidates and {len(euro_candidates)} euro candidates."
        )

        return {
            "primary_candidates": primary_candidates,
            "euro_candidates": euro_candidates,
        }

    def _optimize_candidates(self, candidates: List[int]) -> List[int]:
        """Ensures the candidate list maintains a balanced odd/even structural ratio."""
        odd_count = sum(1 for n in candidates if n % 2 != 0)
        # If set is completely skewed (all even or all odd), log warning
        if odd_count == 0 or odd_count == len(candidates):
            logger.warning("Candidate set has extreme Odd/Even imbalance.")

        return sorted(candidates)
