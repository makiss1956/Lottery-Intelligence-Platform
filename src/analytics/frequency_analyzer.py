"""
Frequency and Delay Statistical Analyzer for Lottery Intelligence Platform.

Calculates base statistical metrics such as frequencies, delay scores,
and historical distributions for standard numbers and bonus Euro numbers.
"""

from collections import Counter
from typing import Any, Dict, List, Tuple

from src.core.logger import get_logger
from src.database.database_manager import DatabaseManager

logger = get_logger("FrequencyAnalyzer")


class FrequencyAnalyzer:
    """Provides statistical frequency and delay analysis over historical lottery draws."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize analyzer with active DatabaseManager instance.

        Args:
            db_manager (DatabaseManager): Connected database manager instance.
        """
        self.db_manager = db_manager

    def fetch_all_draws(self) -> List[Tuple[Any, ...]]:
        """Retrieves all draw records ordered by date descending."""
        query = """
            SELECT draw_date, num1, num2, num3, num4, num5, euro1, euro2
            FROM eurojackpot_draws
            ORDER BY draw_date DESC
        """
        return self.db_manager.fetch_all(query)

    def calculate_number_frequencies(self) -> Dict[int, int]:
        """Calculates total occurrences of main numbers (1-50).

        Returns:
            Dict[int, int]: Dictionary mapping main numbers to their draw counts.
        """
        draws = self.fetch_all_draws()
        counts: Counter[int] = Counter()

        for draw in draws:
            # Main numbers are positions 1 through 5
            main_nums = draw[1:6]
            counts.update(main_nums)

        # Ensure all numbers 1-50 are represented in the map
        return {num: counts.get(num, 0) for num in range(1, 51)}

    def calculate_euro_frequencies(self) -> Dict[int, int]:
        """Calculates total occurrences of Euro numbers (1-12).

        Returns:
            Dict[int, int]: Dictionary mapping Euro numbers to their draw counts.
        """
        draws = self.fetch_all_draws()
        counts: Counter[int] = Counter()

        for draw in draws:
            # Euro numbers are positions 6 and 7
            euro_nums = draw[6:8]
            counts.update(euro_nums)

        return {num: counts.get(num, 0) for num in range(1, 13)}

    def calculate_delays(self) -> Dict[int, int]:
        """Calculates current delays (draws passed since last drawn) for numbers 1-50.

        Returns:
            Dict[int, int]: Dictionary mapping main numbers to their draw delay.
        """
        draws = self.fetch_all_draws()
        delays: Dict[int, int] = {}
        unseen_numbers = set(range(1, 51))

        for idx, draw in enumerate(draws):
            main_nums = set(draw[1:6])
            found_now = unseen_numbers.intersection(main_nums)

            for num in found_now:
                delays[num] = idx
                unseen_numbers.remove(num)

            if not unseen_numbers:
                break

        # Any number never drawn in history gets full dataset length delay
        for num in unseen_numbers:
            delays[num] = len(draws)

        return dict(sorted(delays.items()))

    def get_summary_report(self) -> Dict[str, Any]:
        """Generates a complete frequency and delay summary report.

        Returns:
            Dict[str, Any]: Consolidated metrics summary.
        """
        freqs = self.calculate_number_frequencies()
        euro_freqs = self.calculate_euro_frequencies()
        delays = self.calculate_delays()

        logger.info("Generated frequency and delay summary report.")

        return {
            "total_draws_analyzed": len(self.fetch_all_draws()),
            "main_frequencies": freqs,
            "euro_frequencies": euro_freqs,
            "main_delays": delays,
        }
