"""
Frequency Analyzer Module
-------------------------
Calculates frequencies, delays, and historical distribution metrics for draws.
Includes internal caching to avoid redundant calculations over static datasets.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class FrequencyAnalyzer:
    """Analyzes number frequency and delay statistics with dynamic cache management."""

    def __init__(self, database_connection: Optional[Any] = None):
        """
        Initialize the FrequencyAnalyzer.

        :param database_connection: Connection instance to the persistent store.
        """
        self.db_conn = database_connection
        self.draws_data: List[Dict[str, Any]] = []
        
        # Cache containers
        self._primary_freq_cache: Optional[Dict[int, int]] = None
        self._euro_freq_cache: Optional[Dict[int, int]] = None
        self._delays_cache: Optional[Dict[int, int]] = None

    def invalidate_cache(self) -> None:
        """
        Clears all cached calculation metrics. 
        Must be invoked whenever new draw data is inserted or modified.
        """
        self._primary_freq_cache = None
        self._euro_freq_cache = None
        self._delays_cache = None
        logger.debug("FrequencyAnalyzer cache invalidated successfully.")

    def load_draws(self, draws: List[Dict[str, Any]]) -> None:
        """
        Loads a fresh dataset of draws and invalidates previous cache.

        :param draws: List of draw dictionaries.
        """
        self.draws_data = draws
        self.invalidate_cache()

    def insert_draw(self, draw: Dict[str, Any]) -> None:
        """
        Inserts a single new draw into the local dataset and invalidates the cache.

        :param draw: Dictionary containing draw details (e.g., primary_numbers, euro_numbers).
        """
        self.draws_data.append(draw)
        # Ακύρωση cache για να αποφευχθεί η χρήση stale data στα επόμενα predictions
        self.invalidate_cache()
        logger.info("Inserted new draw and invalidated frequency cache.")

    def calculate_number_frequencies(self) -> Dict[int, int]:
        """
        Calculates occurrence frequencies for primary numbers with caching.

        :return: Dictionary mapping primary numbers to their appearance count.
        """
        if self._primary_freq_cache is not None:
            return self._primary_freq_cache

        freqs: Dict[int, int] = {}
        for draw in self.draws_data:
            numbers = draw.get("primary_numbers") or draw.get("winning_numbers") or []
            for num in numbers:
                freqs[num] = freqs.get(num, 0) + 1

        self._primary_freq_cache = freqs
        return self._primary_freq_cache

    def calculate_euro_frequencies(self) -> Dict[int, int]:
        """
        Calculates occurrence frequencies for euro/bonus numbers with caching.

        :return: Dictionary mapping euro numbers to their appearance count.
        """
        if self._euro_freq_cache is not None:
            return self._euro_freq_cache

        freqs: Dict[int, int] = {}
        for draw in self.draws_data:
            numbers = draw.get("euro_numbers") or draw.get("bonus_numbers") or []
            for num in numbers:
                freqs[num] = freqs.get(num, 0) + 1

        self._euro_freq_cache = freqs
        return self._euro_freq_cache

    def calculate_delays(self) -> Dict[int, int]:
        """
        Calculates the current delay (draws since last appearance) for primary numbers.

        :return: Dictionary mapping primary numbers to their current delay count.
        """
        if self._delays_cache is not None:
            return self._delays_cache

        delays: Dict[int, int] = {}
        # Υπολογισμός καθυστερήσεων ξεκινώντας από την πιο πρόσφατη κλήρωση
        for index, draw in enumerate(reversed(self.draws_data)):
            numbers = draw.get("primary_numbers") or draw.get("winning_numbers") or []
            for num in numbers:
                if num not in delays:
                    delays[num] = index

        self._delays_cache = delays
        return self._delays_cache
