"""Frequency, delay and hot/cold analytics."""
from typing import Dict, List, Tuple, Optional, Any
from src.core.cache import get_cache
from src.core.logger import get_logger

logger = get_logger("FrequencyAnalyzer")

class FrequencyAnalyzer:
    """Analyzes draw history for statistical patterns."""

    def __init__(self, db_manager):
        self.db = db_manager
        self.cache = get_cache()

    def get_all_draws(self) -> List[Dict]:
        """Fetch all draws from DB, newest first."""
        draws = self.db.get_all_draws()
        return list(reversed(draws))  # Newest first

    def get_primary_frequencies(self) -> Dict[int, int]:
        """Count occurrences of each primary number (1-50)."""
        cached = self.cache.get("primary_frequencies")
        if cached is not None:
            return cached
        draws = self.get_all_draws()
        counts = {i: 0 for i in range(1, 51)}
        for draw in draws:
            for num in draw["primary_numbers"]:
                if 1 <= num <= 50:
                    counts[num] += 1
        self.cache.set("primary_frequencies", counts)
        return counts

    def get_euro_frequencies(self) -> Dict[int, int]:
        """Count occurrences of each Euro number (1-12)."""
        cached = self.cache.get("euro_frequencies")
        if cached is not None:
            return cached
        draws = self.get_all_draws()
        counts = {i: 0 for i in range(1, 13)}
        for draw in draws:
            for num in draw["euro_numbers"]:
                if 1 <= num <= 12:
                    counts[num] += 1
        self.cache.set("euro_frequencies", counts)
        return counts

    def calculate_delays(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Draws passed since each number last appeared."""
        cached = self.cache.get("delays")
        if cached is not None:
            return cached
        draws = self.get_all_draws()
        total = len(draws)
        primary_delays = {i: total for i in range(1, 51)}
        euro_delays = {i: total for i in range(1, 13)}

        for idx, draw in enumerate(draws):
            for num in draw["primary_numbers"]:
                if primary_delays[num] == total:
                    primary_delays[num] = idx
            for num in draw["euro_numbers"]:
                if euro_delays[num] == total:
                    euro_delays[num] = idx

        result = (primary_delays, euro_delays)
        self.cache.set("delays", result)
        return result

    def get_hot_numbers(self, count: int = 7) -> List[int]:
        """Most frequent primary numbers."""
        freqs = self.get_primary_frequencies()
        return [num for num, _ in sorted(freqs.items(), key=lambda x: x[1], reverse=True)[:count]]

    def get_cold_numbers(self, count: int = 7) -> List[int]:
        """Least frequent primary numbers."""
        freqs = self.get_primary_frequencies()
        return [num for num, _ in sorted(freqs.items(), key=lambda x: x[1])[:count]]

    def get_stats_summary(self) -> Dict[str, Any]:
        """Quick stats for reporting."""
        pfreq = self.get_primary_frequencies()
        efreq = self.get_euro_frequencies()
        p_delay, e_delay = self.calculate_delays()
        total_draws = len(self.get_all_draws())
        return {
            "total_draws": total_draws,
            "hot_primary": self.get_hot_numbers(5),
            "cold_primary": self.get_cold_numbers(5),
            "hot_euro": [num for num, _ in sorted(efreq.items(), key=lambda x: x[1], reverse=True)[:3]],
            "most_overdue_primary": sorted(
                [(n, p_delay[n]) for n in range(1, 51)], key=lambda x: x[1], reverse=True
            )[:5],
            "most_overdue_euro": sorted(
                [(n, e_delay[n]) for n in range(1, 13)], key=lambda x: x[1], reverse=True
            )[:3],
        }
