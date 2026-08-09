"""
Frequency and Delay Analyzer for Eurojackpot draw data.
Calculates occurrence statistics and draws-since-last-seen metrics.
"""

from typing import Dict, List, Tuple
from src.core.cache import get_cache
from src.database.database_manager import DatabaseManager


class FrequencyAnalyzer:
    """Analyzes historical draw data to extract statistical distribution metrics."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.cache = get_cache()

    def get_all_draws(self) -> List[Dict]:
        """Fetch all stored draws from the database, newest first."""
        query = """
        SELECT draw_date, num1, num2, num3, num4, num5, euro1, euro2
        FROM eurojackpot_draws
        ORDER BY draw_date DESC
        """
        rows = self.db_manager.fetch_all(query)
        return [
            {
                "draw_date": row[0],
                "numbers": list(row[1:6]),
                "euro_numbers": list(row[6:8]),
            }
            for row in rows
        ]

    def calculate_number_frequencies(self) -> Dict[int, int]:
        """Count occurrences of each primary number (1 to 50) with caching."""
        cached = self.cache.get("primary_frequencies")
        if cached is not None:
            return cached

        draws = self.get_all_draws()
        counts = {i: 0 for i in range(1, 51)}
        for draw in draws:
            for num in draw["numbers"]:
                if num in counts:
                    counts[num] += 1

        self.cache.set("primary_frequencies", counts)
        return counts

    def calculate_euro_frequencies(self) -> Dict[int, int]:
        """Count occurrences of each Euro number (1 to 12) with caching."""
        cached = self.cache.get("euro_frequencies")
        if cached is not None:
            return cached

        draws = self.get_all_draws()
        counts = {i: 0 for i in range(1, 13)}
        for draw in draws:
            for num in draw["euro_numbers"]:
                if num in counts:
                    counts[num] += 1

        self.cache.set("euro_frequencies", counts)
        return counts

    def calculate_delays(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Calculate draws passed since each number last appeared with caching."""
        cached = self.cache.get("delays")
        if cached is not None:
            return cached

        draws = self.get_all_draws()
        primary_delays = {i: len(draws) for i in range(1, 51)}
        euro_delays = {i: len(draws) for i in range(1, 13)}

        for index, draw in enumerate(draws):
            for num in draw["numbers"]:
                if primary_delays[num] == len(draws):
                    primary_delays[num] = index

            for num in draw["euro_numbers"]:
                if euro_delays[num] == len(draws):
                    euro_delays[num] = index

        result = (primary_delays, euro_delays)
        self.cache.set("delays", result)
        return result
