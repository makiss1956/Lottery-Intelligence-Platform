"""
Pattern Analytics Module for Lottery Intelligence Platform.

Analyzes structural characteristics of draw history including Odd/Even ratios,
High/Low distributions, and Sum range patterns to refine probability models.
"""

from typing import Any, Dict, List, Tuple
from src.core.logger import get_logger

logger = get_logger("PatternAnalyzer")


class PatternAnalyzer:
    """Extracts structural patterns from historical draw data."""

    def __init__(self, db_manager: Any):
        """Initializes analyzer with database connection manager."""
        self.db_manager = db_manager

    def fetch_all_draws(self) -> List[Tuple]:
        """Fetches historical draws ordered by date descending."""
        query = """
            SELECT draw_date, num1, num2, num3, num4, num5, euro1, euro2
            FROM eurojackpot_draws
            ORDER BY draw_date DESC
        """
        return self.db_manager.fetch_all(query)

    def analyze_odd_even_distribution(self) -> Dict[str, int]:
        """Calculates occurrences of Odd/Even ratios across primary numbers.

        Returns:
            Dict[str, int]: Distribution map, e.g., {"3_odd_2_even": 42}
        """
        draws = self.fetch_all_draws()
        distribution: Dict[str, int] = {}

        for draw in draws:
            mains = list(draw[1:6])
            odd_count = sum(1 for n in mains if n % 2 != 0)
            even_count = 5 - odd_count
            key = f"{odd_count}_odd_{even_count}_even"
            distribution[key] = distribution.get(key, 0) + 1

        logger.info(f"Odd/Even distribution calculated over {len(draws)} draws.")
        return distribution

    def analyze_high_low_distribution(self, cutoff: int = 25) -> Dict[str, int]:
        """Calculates occurrences of High/Low split (Low <= cutoff, High > cutoff).

        Returns:
            Dict[str, int]: Distribution map, e.g., {"3_low_2_high": 38}
        """
        draws = self.fetch_all_draws()
        distribution: Dict[str, int] = {}

        for draw in draws:
            mains = list(draw[1:6])
            low_count = sum(1 for n in mains if n <= cutoff)
            high_count = 5 - low_count
            key = f"{low_count}_low_{high_count}_high"
            distribution[key] = distribution.get(key, 0) + 1

        logger.info(f"High/Low distribution calculated over {len(draws)} draws.")
        return distribution

    def analyze_sum_ranges(self) -> Dict[str, Any]:
        """Calculates min, max, average, and median sum of primary numbers."""
        draws = self.fetch_all_draws()
        if not draws:
            return {"min_sum": 0, "max_sum": 0, "avg_sum": 0.0}

        sums = [sum(draw[1:6]) for draw in draws]
        avg_sum = sum(sums) / len(sums)

        return {
            "min_sum": min(sums),
            "max_sum": max(sums),
            "avg_sum": round(avg_sum, 2),
            "total_analyzed": len(sums),
        }
