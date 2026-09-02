"""Probability Prediction Engine with Composite Scoring."""
from typing import Any, Dict, List
import random
from src.core.logger import get_logger

logger = get_logger("Predictor")


class ProbabilityPredictor:
    """
    Composite scoring predictor.
    Score = (frequency_weight * normalized_frequency) - (delay_weight * normalized_delay)
    Hot numbers (high freq, low delay) -> high score
    Cold numbers (low freq, high delay) -> low/negative score -> rejected
    """

    def __init__(self, frequency_analyzer, pattern_analyzer=None,
                 frequency_weight: float = 0.7,
                 delay_weight: float = 0.3):
        self.freq_analyzer = frequency_analyzer
        self.pattern_analyzer = pattern_analyzer
        self.frequency_weight = frequency_weight
        self.delay_weight = delay_weight

    def predict_candidate_set(self, primary_count: int = 7, euro_count: int = 3) -> Dict[str, Any]:
        # --- Primary Numbers Scoring ---
        primary_freqs = self.freq_analyzer.get_primary_frequencies()
        primary_delays, _ = self.freq_analyzer.calculate_delays()
        primary_scores = self._compute_scores(primary_freqs, primary_delays, 1, 50)
        # Sort by score DESC (most probable first)
        sorted_primary = sorted(primary_scores.items(), key=lambda x: x[1], reverse=True)

        # --- Euro Numbers Scoring ---
        euro_freqs = self.freq_analyzer.get_euro_frequencies()
        _, euro_delays = self.freq_analyzer.calculate_delays()
        euro_scores = self._compute_scores(euro_freqs, euro_delays, 1, 12)
        sorted_euro = sorted(euro_scores.items(), key=lambda x: x[1], reverse=True)

        # --- Select top candidates ---
        primary_candidates = [num for num, score in sorted_primary[:primary_count]]
        euro_candidates = [num for num, score in sorted_euro[:euro_count]]

        # --- Pattern optimization ---
        if self.pattern_analyzer:
            primary_candidates = self._optimize_candidates(
                primary_candidates,
                [num for num, _ in sorted_primary[primary_count:primary_count+10]]
            )

        # ==============================================
        # === ΔΙΟΡΘΩΣΗ: Διασφάλιση σωστού αριθμού ===
        # ==============================================

        # Διασφάλιση ακριβώς 7 μοναδικών κύριων αριθμών
        primary_candidates = sorted(list(set(primary_candidates)))
        while len(primary_candidates) < primary_count:
            # Βρίσκουμε αριθμούς που λείπουν (1-50)
            missing = [n for n in range(1, 51) if n not in primary_candidates]
            if missing:
                # Προσθέτουμε τον αριθμό με την υψηλότερη βαθμολογία που λείπει
                for num, _ in sorted_primary:
                    if num in missing:
                        primary_candidates.append(num)
                        break
        primary_candidates = sorted(primary_candidates[:primary_count])

        # Διασφάλιση ακριβώς 3 μοναδικών Ευρώ αριθμών
        euro_candidates = sorted(list(set(euro_candidates)))
        while len(euro_candidates) < euro_count:
            missing = [n for n in range(1, 13) if n not in euro_candidates]
            if missing:
                for num, _ in sorted_euro:
                    if num in missing:
                        euro_candidates.append(num)
                        break
        euro_candidates = sorted(euro_candidates[:euro_count])

        # Έλεγχος — Πρέπει πλέον να είναι σωστά
        if len(primary_candidates) != primary_count:
            logger.error(f"ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: Βρέθηκαν {len(primary_candidates)} αντί για {primary_count} κύριοι αριθμοί!")
        if len(euro_candidates) != euro_count:
            logger.error(f"ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: Βρέθηκαν {len(euro_candidates)} αντί για {euro_count} Ευρώ αριθμοί!")

        logger.info("Generated %s primary and %s euro candidates.", len(primary_candidates), len(euro_candidates))

        # ==============================================
        # === ΤΕΛΟΣ ΔΙΟΡΘΩΣΗΣ ===
        # ==============================================

        primary_conf = {n: round(primary_scores[n], 4) for n in primary_candidates}
        euro_conf = {n: round(euro_scores[n], 4) for n in euro_candidates}

        return {
            "primary_candidates": primary_candidates,
            "euro_candidates": euro_candidates,
            "method": "composite_freq_delay",
            "confidence": {
                "primary": primary_conf,
                "euro": euro_conf
            },
            "primary_scores": {n: round(s, 4) for n, s in sorted_primary[:primary_count]},
            "euro_scores": {n: round(s, 4) for n, s in sorted_euro[:euro_count]}
        }

    def _compute_scores(self, freqs: Dict[int, int], delays: Dict[int, int],
                        min_num: int, max_num: int) -> Dict[int, float]:
        max_freq = max(freqs.values()) if freqs else 1
        min_freq = min(freqs.values()) if freqs else 0
        freq_range = max_freq - min_freq if max_freq != min_freq else 1

        max_delay = max(delays.values()) if delays else 1
        min_delay = min(delays.values()) if delays else 0
        delay_range = max_delay - min_delay if max_delay != min_delay else 1

        scores = {}
        for num in range(min_num, max_num + 1):
            norm_freq = (freqs.get(num, 0) - min_freq) / freq_range
            norm_delay = (delays.get(num, 0) - min_delay) / delay_range
            score = (self.frequency_weight * norm_freq) - (self.delay_weight * norm_delay)
            scores[num] = score
        return scores

    def _optimize_candidates(self, candidates: List[int], extended_pool: List[int]) -> List[int]:
        if not candidates or not extended_pool:
            return candidates

        # Remove duplicates while preserving order
        candidates = list(dict.fromkeys(candidates))

        odd = sum(1 for n in candidates if n % 2 != 0)
        even = len(candidates) - odd

        if odd == 0 or even == 0:
            target_odd = (odd == 0)
            replacement = next((n for n in extended_pool if (n % 2 != 0) == target_odd and n not in candidates), None)
            if replacement is not None:
                removed = candidates.pop()
                candidates.append(replacement)
                logger.info("Rebalanced odd/even: replaced %s with %s.", removed, replacement)

        current_sum = sum(candidates)
        if current_sum < 90 or current_sum > 160:
            for i, num in enumerate(candidates):
                for repl in extended_pool:
                    if repl in candidates:
                        continue
                    new_sum = current_sum - num + repl
                    if 90 <= new_sum <= 160:
                        candidates[i] = repl
                        logger.info("Sum rebalanced: %s -> %s (sum now %s)", num, repl, new_sum)
                        return candidates

        return candidates
