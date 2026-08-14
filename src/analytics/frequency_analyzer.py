"""Frequency and Delay Analysis Engine."""
from typing import Dict, List, Tuple
from src.core.logger import get_logger

logger = get_logger("FrequencyAnalyzer")

class SimpleCache:
    def __init__(self):
        self._store = {}
    def get(self, key: str):
        return self._store.get(key)
    def set(self, key: str, value):
        self._store[key] = value

class FrequencyAnalyzer:
    def __init__(self, db_manager):
        self.db_mgr = db_manager
        self.cache = SimpleCache()

    def get_all_draws(self) -> List[dict]:
        cached = self.cache.get("all_draws")
        if cached is not None:
            return cached
        draws = self.db_mgr.get_all_draws()
        self.cache.set("all_draws", draws)
        return draws

    def get_primary_frequencies(self) -> Dict[int, int]:
        draws = self.get_all_draws()
        freqs = {i: 0 for i in range(1, 51)}
        for d in draws:
            for num in d.get("primary_numbers", []):
                if 1 <= num <= 50:
                    freqs[num] += 1
        return freqs

    def get_euro_frequencies(self) -> Dict[int, int]:
        draws = self.get_all_draws()
        freqs = {i: 0 for i in range(1, 13)}
        for d in draws:
            for num in d.get("euro_numbers", []):
                if 1 <= num <= 12:
                    freqs[num] += 1
        return freqs

    def calculate_delays(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        cached = self.cache.get("delays")
        if cached is not None:
            return cached
        draws = self.get_all_draws()
        total = len(draws)

        primary_delays = {i: -1 for i in range(1, 51)}
        euro_delays = {i: -1 for i in range(1, 13)}

        for idx, draw in enumerate(draws):
            for num in draw.get("primary_numbers", []):
                if 1 <= num <= 50 and primary_delays[num] == -1:
                    primary_delays[num] = idx
            for num in draw.get("euro_numbers", []):
                if 1 <= num <= 12 and euro_delays[num] == -1:
                    euro_delays[num] = idx

        for num in range(1, 51):
            if primary_delays[num] == -1:
                primary_delays[num] = total + 1
        for num in range(1, 13):
            if euro_delays[num] == -1:
                euro_delays[num] = total + 1

        result = (primary_delays, euro_delays)
        self.cache.set("delays", result)
        return result

    def get_markov_transitions(self) -> Dict[int, Dict[int, float]]:
        draws = self.get_all_draws()
        transitions = {i: {j: 0 for j in range(1, 51)} for i in range(1, 51)}
        counts = {i: 0 for i in range(1, 51)}

        for draw in draws:
            nums = sorted(draw.get("primary_numbers", []))
            for i, a in enumerate(nums):
                for b in nums[i+1:]:
                    if 1 <= a <= 50 and 1 <= b <= 50:
                        transitions[a][b] += 1
                        transitions[b][a] += 1
                        counts[a] += 1
                        counts[b] += 1

        for a in range(1, 51):
            if counts[a] > 0:
                for b in range(1, 51):
                    transitions[a][b] /= counts[a]
        return transitions

    def get_gap_analysis(self) -> Dict[int, List[int]]:
        draws = self.get_all_draws()[::-1]
        gaps = {i: [] for i in range(1, 51)}
        last_seen = {i: None for i in range(1, 51)}

        for idx, draw in enumerate(draws):
            for num in draw.get("primary_numbers", []):
                if 1 <= num <= 50:
                    if last_seen[num] is not None:
                        gaps[num].append(idx - last_seen[num])
                    last_seen[num] = idx

        return gaps

    def get_recency_weighted_frequency(self, decay: float = 0.95) -> Dict[int, float]:
        draws = self.get_all_draws()
        scores = {i: 0.0 for i in range(1, 51)}

        for idx, draw in enumerate(draws):
            weight = decay ** idx
            for num in draw.get("primary_numbers", []):
                if 1 <= num <= 50:
                    scores[num] += weight

        return scores
