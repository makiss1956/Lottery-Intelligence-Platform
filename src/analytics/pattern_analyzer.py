"""Structural pattern analysis (odd/even, sum ranges, etc)."""
from typing import List, Dict, Any
from src.core.logger import get_logger

logger = get_logger("PatternAnalyzer")

class PatternAnalyzer:
    """Analyzes structural properties of number sets."""

    @staticmethod
    def odd_even_balance(numbers: List[int]) -> Dict[str, int]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        even = len(numbers) - odd
        return {"odd": odd, "even": even, "ratio": f"{odd}:{even}"}

    @staticmethod
    def sum_range(numbers: List[int]) -> int:
        return sum(numbers)

    @staticmethod
    def consecutive_count(numbers: List[int]) -> int:
        s = sorted(numbers)
        cons = 0
        for i in range(len(s) - 1):
            if s[i+1] - s[i] == 1:
                cons += 1
        return cons

    @staticmethod
    def decade_distribution(numbers: List[int]) -> Dict[str, int]:
        dist = {"1-10": 0, "11-20": 0, "21-30": 0, "31-40": 0, "41-50": 0}
        for n in numbers:
            if 1 <= n <= 10: dist["1-10"] += 1
            elif 11 <= n <= 20: dist["11-20"] += 1
            elif 21 <= n <= 30: dist["21-30"] += 1
            elif 31 <= n <= 40: dist["31-40"] += 1
            elif 41 <= n <= 50: dist["41-50"] += 1
        return dist

    def analyze_draw(self, draw: Dict[str, Any]) -> Dict[str, Any]:
        primary = draw.get("primary_numbers", [])
        return {
            "odd_even": self.odd_even_balance(primary),
            "sum": self.sum_range(primary),
            "consecutive": self.consecutive_count(primary),
            "decades": self.decade_distribution(primary)
        }
