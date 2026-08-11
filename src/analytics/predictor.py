"""Probability Prediction Engine."""
from typing import Any, Dict, List
from src.core.logger import get_logger

logger = get_logger("Predictor")

class ProbabilityPredictor:
    """Ranks candidates using frequency + pattern optimization."""

    def __init__(self, frequency_analyzer, pattern_analyzer=None):
        self.freq_analyzer = frequency_analyzer
        self.pattern_analyzer = pattern_analyzer

    def predict_candidate_set(self, primary_count: int = 7, euro_count: int = 3) -> Dict[str, Any]:
        primary_freqs = self.freq_analyzer.get_primary_frequencies()
        euro_freqs = self.freq_analyzer.get_euro_frequencies()

        sorted_primary = [num for num, _ in sorted(primary_freqs.items(), key=lambda x: x[1], reverse=True)]
        sorted_euro = [num for num, _ in sorted(euro_freqs.items(), key=lambda x: x[1], reverse=True)]

        # Safety checks
        if len(sorted_primary) < primary_count:
            logger.warning("Only %s primary numbers available, requested %s.", len(sorted_primary), primary_count)
            primary_count = len(sorted_primary)
        if len(sorted_euro) < euro_count:
            logger.warning("Only %s euro numbers available, requested %s.", len(sorted_euro), euro_count)
            euro_count = len(sorted_euro)

        primary_candidates = sorted_primary[:primary_count]
        euro_candidates = sorted_euro[:euro_count]

        # Pattern optimization
        if self.pattern_analyzer:
            extended = sorted_primary[primary_count:]
            primary_candidates = self._optimize_candidates(primary_candidates, extended)

        logger.info("Generated %s primary and %s euro candidates.", len(primary_candidates), len(euro_candidates))

        return {
            "primary_candidates": sorted(primary_candidates),
            "euro_candidates": sorted(euro_candidates),
            "method": "frequency_7_3",
            "confidence": {
                "primary": {n: primary_freqs[n] for n in primary_candidates},
                "euro": {n: euro_freqs[n] for n in euro_candidates}
            }
        }

    def _optimize_candidates(self, candidates: List[int], extended_pool: List[int]) -> List[int]:
        """Rebalance odd/even if extreme."""
        if not candidates or not extended_pool:
            return candidates
        odd = sum(1 for n in candidates if n % 2 != 0)
        even = len(candidates) - odd

        if odd == 0 or even == 0:
            target_odd = (odd == 0)
            replacement = next((n for n in extended_pool if (n % 2 != 0) == target_odd), None)
            if replacement is not None:
                removed = candidates.pop()
                candidates.append(replacement)
                logger.info("Rebalanced: replaced %s with %s.", removed, replacement)
        return sorted(candidates)
