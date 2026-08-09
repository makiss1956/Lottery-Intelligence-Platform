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

        # Safety checks for small datasets / empty database
        if len(sorted_primary) < primary_count:
            logger.warning(
                f"Only {len(sorted_primary)} primary numbers available, requested {primary_count}."
            )
            primary_count = len(sorted_primary)

        if len(sorted_euro) < euro_count:
            logger.warning(
                f"Only {len(sorted_euro)} euro numbers available, requested {euro_count}."
            )
            euro_count = len(sorted_euro)

        primary_candidates = sorted_primary[:primary_count]
        euro_candidates = sorted_euro[:euro_count]

        # Apply structural pattern optimization if PatternAnalyzer is available
        if self.pattern_analyzer:
            extended_pool = sorted_primary[primary_count:]
            primary_candidates = self._optimize_candidates(primary_candidates, extended_pool)

        logger.info(
            f"Generated {len(primary_candidates)} primary candidates and {len(euro_candidates)} euro candidates."
        )

        return {
            "primary_candidates": primary_candidates,
            "euro_candidates": euro_candidates,
        }

    def _optimize_candidates(self, candidates: List[int], extended_pool: List[int] = None) -> List[int]:
        """Ensures the candidate list maintains a balanced odd/even structural ratio."""
        if not candidates:
            return candidates

        odd_count = sum(1 for n in candidates if n % 2 != 0)
        even_count = len(candidates) - odd_count

        # Ανίχνευση ακραίας ανισορροπίας (όλοι μονοί ή όλοι ζυγοί)
        if (odd_count == 0 or even_count == 0) and extended_pool:
            logger.warning("Extreme Odd/Even imbalance detected. Attempting rebalance via extended pool swap.")
            target_is_odd = (odd_count == 0)  # Αν έχουμε 0 μονούς, ψάχνουμε έναν μονό στο pool
            
            # Αναζήτηση του πρώτου αριθμού με την αντίθετη αρτιότητα από το extended pool
            replacement_num = next((num for num in extended_pool if (num % 2 != 0) == target_is_odd), None)
            
            if replacement_num is not None:
                removed_num = candidates.pop()  # Αφαίρεση του τελευταίου (χαμηλότερης συχνότητας) υποψηφίου
                candidates.append(replacement_num)
                logger.info(f"Rebalanced candidate set: replaced {removed_num} with {replacement_num}.")

        return sorted(candidates)
