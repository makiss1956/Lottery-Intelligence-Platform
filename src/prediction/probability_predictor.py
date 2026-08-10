"""
Probability Predictor Module
---------------------------
Calculates draw probabilities for candidate number sets based on 
historical frequency analysis and statistical metrics.
"""

import logging
from typing import Dict, List, Tuple, Any, Optional, Set

logger = logging.getLogger(__name__)


class ProbabilityPredictor:
    """Predictor that utilizes statistical frequency analysis to score and rank candidate sets."""

    def __init__(self, freq_analyzer: Any):
        """
        Initialize the predictor with a FrequencyAnalyzer instance.

        :param freq_analyzer: An instance of FrequencyAnalyzer.
        """
        self.freq_analyzer = freq_analyzer

    def rebalance_candidates(
        self, 
        candidates: List[int], 
        frequencies: Dict[int, int], 
        replacement_pool: List[int]
    ) -> List[int]:
        """
        Safely rebalances a list of candidate numbers by removing the element 
        with the lowest frequency score and introducing a replacement.

        :param candidates: Current list of candidate numbers.
        :param frequencies: Dictionary mapping numbers to their historical frequencies.
        :param replacement_pool: Pool of eligible numbers for replacement.
        :return: Rebalanced list of candidate numbers sorted in ascending order.
        """
        if not candidates:
            return []

        # 1. Ταξινόμηση υποψηφίων βάσει συχνότητας (αύξουσα σειρά: πρώτο το στοιχείο με τη μικρότερη συχνότητα)
        sorted_by_freq = sorted(candidates, key=lambda num: frequencies.get(num, 0))

        # 2. Αφαίρεση του αριθμού με τη χαμηλότερη συχνότητα
        lowest_freq_num = sorted_by_freq.pop(0)
        remaining_candidates = set(sorted_by_freq)

        # 3. Εύρεση κατάλληλου αντικαταστάτη που δεν υπάρχει ήδη στους υποψηφίους
        replacement = None
        for num in replacement_pool:
            if num not in remaining_candidates and num != lowest_freq_num:
                replacement = num
                break

        if replacement is not None:
            remaining_candidates.add(replacement)
            logger.debug("Rebalanced: Removed %d (freq: %d), Added %d", 
                         lowest_freq_num, frequencies.get(lowest_freq_num, 0), replacement)
        else:
            remaining_candidates.add(lowest_freq_num)  # Fallback αν δεν βρεθεί αντικαταστάτης

        # 4. Επιστροφή ταξινομημένης λίστας κατά αύξουσα αριθμητική σειρά για το τελικό output
        return sorted(list(remaining_candidates))

    def predict_candidate_set(
        self, 
        primary_numbers: Optional[List[int]] = None, 
        euro_numbers: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Calculates score and probability metrics for a set of candidate numbers.

        :param primary_numbers: List of primary numbers chosen for candidate evaluation.
        :param euro_numbers: List of euro numbers chosen for candidate evaluation.
        :return: Dictionary containing statistical scores and calculated weights.
        """
        try:
            primary_freqs = self.freq_analyzer.calculate_number_frequencies()
            euro_freqs = self.freq_analyzer.calculate_euro_frequencies()
        except AttributeError as e:
            logger.error("Error invoking frequency calculation methods on FrequencyAnalyzer: %s", e)
            raise AttributeError(
                "FrequencyAnalyzer does not implement 'calculate_number_frequencies' "
                "or 'calculate_euro_frequencies'."
            ) from e

        # Υπολογισμός σκορ για τους κύριους αριθμούς
        primary_score = 0.0
        if primary_numbers and isinstance(primary_freqs, dict):
            total_primary_draws = sum(primary_freqs.values()) if primary_freqs else 1
            for num in primary_numbers:
                count = primary_freqs.get(num, 0)
                primary_score += count / total_primary_draws if total_primary_draws > 0 else 0.0

        # Υπολογισμός σκορ για τους αριθμούς Euro / Bonus
        euro_score = 0.0
        if euro_numbers and isinstance(euro_freqs, dict):
            total_euro_draws = sum(euro_freqs.values()) if euro_freqs else 1
            for num in euro_numbers:
                count = euro_freqs.get(num, 0)
                euro_score += count / total_euro_draws if total_euro_draws > 0 else 0.0

        total_score = primary_score + euro_score

        return {
            "primary_numbers": primary_numbers or [],
            "euro_numbers": euro_numbers or [],
            "primary_score": round(primary_score, 5),
            "euro_score": round(euro_score, 5),
            "total_score": round(total_score, 5),
            "status": "success"
        }

    def rank_candidates(self, candidate_list: List[Dict[str, List[int]]]) -> List[Dict[str, Any]]:
        """
        Ranks a list of candidate sets based on their calculated total probability score.

        :param candidate_list: List of dicts, e.g., [{"primary": [1, 2, 3, 4, 5], "euro": [1, 2]}]
        :return: Sorted list of evaluated candidate sets in descending order of score.
        """
        results = []
        for candidate in candidate_list:
            primaries = candidate.get("primary", [])
            euros = candidate.get("euro", [])
            evaluation = self.predict_candidate_set(primary_numbers=primaries, euro_numbers=euros)
            results.append(evaluation)

        results.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
        return results
