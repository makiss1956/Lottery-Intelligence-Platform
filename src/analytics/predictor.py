"""Probability Prediction Engine with Composite Scoring."""
from typing import Any, Dict, List
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
                [num for num, _ in sorted_primary[primary_count:primary_count+20]]
            )

        # ==============================================
        # === ΔΙΟΡΘΩΣΗ: ΠΑΝΤΑ ΑΚΡΙΒΩΣ 7 + 3 αριθμοί ===
        # ==============================================
        # Αφαίρεση διπλότυπων διατηρώντας την σειρά
        clean_primary = []
        for num in primary_candidates:
            if num not in clean_primary:
                clean_primary.append(num)

        # Συμπλήρωση αν λείπουν αριθμοί
        if len(clean_primary) < primary_count:
            for num, _ in sorted_primary:
                if num not in clean_primary:
                    clean_primary.append(num)
                    logger.info("✅ Συμπληρώθηκε ο κύριος αριθμός: %s", num)
                    if len(clean_primary) == primary_count:
                        break

        primary_candidates = sorted(clean_primary[:primary_count])

        clean_euro = []
        for num in euro_candidates:
            if num not in clean_euro:
                clean_euro.append(num)

        if len(clean_euro) < euro_count:
            for num, _ in sorted_euro:
                if num not in clean_euro:
                    clean_euro.append(num)
                    logger.info("✅ Συμπληρώθηκε ο αριθμός Euro: %s", num)
                    if len(clean_euro) == euro_count:
                        break

        euro_candidates = sorted(clean_euro[:euro_count])
        # ==============================================

        logger.info("✅ Generated %s primary and %s euro candidates.", len(primary_candidates), len(euro_candidates))

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

        # Διατήρηση μοναδικών τιμών
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
