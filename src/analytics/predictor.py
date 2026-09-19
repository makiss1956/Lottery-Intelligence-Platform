"""Prediction engine for 3 main numbers + 1 Joker/Euro number."""

from typing import Any, Dict

from src.core.logger import get_logger

logger = get_logger("Predictor")

class ProbabilityPredictor:
"""Statistical candidate selector."""

```
def __init__(
    self,
    frequency_analyzer,
    pattern_analyzer=None,
    frequency_weight: float = 0.7,
    delay_weight: float = 0.3,
):
    self.freq_analyzer = frequency_analyzer
    self.pattern_analyzer = pattern_analyzer
    self.frequency_weight = frequency_weight
    self.delay_weight = delay_weight

def predict_candidate_set(
    self,
    primary_count: int = 3,
    euro_count: int = 1,
) -> Dict[str, Any]:

    if primary_count != 3:
        raise ValueError(
            "This model requires exactly 3 main numbers."
        )

    if euro_count != 1:
        raise ValueError(
            "This model requires exactly 1 Joker/Euro number."
        )

    primary_freqs = self.freq_analyzer.get_primary_frequencies()
    primary_delays, _ = self.freq_analyzer.calculate_delays()

    primary_scores = self._compute_scores(
        primary_freqs,
        primary_delays,
        1,
        50,
    )

    sorted_primary = sorted(
        primary_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    primary_candidates = [
        number
        for number, _ in sorted_primary[:primary_count]
    ]

    euro_freqs = self.freq_analyzer.get_euro_frequencies()
    _, euro_delays = self.freq_analyzer.calculate_delays()

    euro_scores = self._compute_scores(
        euro_freqs,
        euro_delays,
        1,
        12,
    )

    sorted_euro = sorted(
        euro_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    euro_candidates = [
        number
        for number, _ in sorted_euro[:euro_count]
    ]

    primary_candidates = sorted(
        list(dict.fromkeys(primary_candidates))
    )

    euro_candidates = sorted(
        list(dict.fromkeys(euro_candidates))
    )

    if len(primary_candidates) != 3:
        raise RuntimeError(
            f"Predictor produced {len(primary_candidates)} main numbers."
        )

    if len(euro_candidates) != 1:
        raise RuntimeError(
            f"Predictor produced {len(euro_candidates)} Joker numbers."
        )

    logger.info(
        "Prediction generated | Main=%s | Joker=%s",
        primary_candidates,
        euro_candidates,
    )

    return {
        "primary_candidates": primary_candidates,
        "euro_candidates": euro_candidates,
        "joker_candidates": euro_candidates,
        "method": "composite_frequency_delay",
        "confidence": {
            "primary": {
                number: round(primary_scores[number], 4)
                for number in primary_candidates
            },
            "joker": {
                number: round(euro_scores[number], 4)
                for number in euro_candidates
            },
        },
        "primary_scores": {
            number: round(score, 4)
            for number, score in sorted_primary[:3]
        },
        "euro_scores": {
            number: round(score, 4)
            for number, score in sorted_euro[:1]
        },
    }

def _compute_scores(
    self,
    freqs: Dict[int, int],
    delays: Dict[int, int],
    min_num: int,
    max_num: int,
) -> Dict[int, float]:

    max_freq = max(freqs.values()) if freqs else 1
    min_freq = min(freqs.values()) if freqs else 0

    freq_range = (
        max_freq - min_freq
        if max_freq != min_freq
        else 1
    )

    max_delay = max(delays.values()) if delays else 1
    min_delay = min(delays.values()) if delays else 0

    delay_range = (
        max_delay - min_delay
        if max_delay != min_delay
        else 1
    )

    scores: Dict[int, float] = {}

    for number in range(min_num, max_num + 1):
        normalized_frequency = (
            (freqs.get(number, 0) - min_freq)
            / freq_range
        )

        normalized_delay = (
            (delays.get(number, 0) - min_delay)
            / delay_range
        )

        score = (
            self.frequency_weight * normalized_frequency
            - self.delay_weight * normalized_delay
        )

        scores[number] = score

    return scores
```
