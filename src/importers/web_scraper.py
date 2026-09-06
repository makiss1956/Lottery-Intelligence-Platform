"""
Web Scraper Module for Eurojackpot draws via OPAP API.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class EurojackpotWebScraper:
    """Scraper to fetch historical Eurojackpot draw results from OPAP API."""

    # ΣΩΣΤΟ GAME_ID για το Eurojackpot στον ΟΠΑΠ είναι το 5109 (Το 5104 είναι το Τζόκερ)
    GAME_ID = 5109
    BASE_URL = f"https://api.opap.gr/draws/v3.0/{GAME_ID}"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        )

    def fetch_draws_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch draws for a date range (YYYY-MM-DD).
        """
        url = f"{self.BASE_URL}/draw-date/{start_date}/{end_date}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Αν επιστραφεί λίστα ή dict με 'content'
            if isinstance(data, dict):
                raw_draws = data.get("content", [])
            elif isinstance(data, list):
                raw_draws = data
            else:
                raw_draws = []

            parsed_draws = []
            for draw in raw_draws:
                parsed = self._parse_draw(draw)
                if parsed:
                    parsed_draws.append(parsed)

            return parsed_draws

        except requests.RequestException as exc:
            logger.error("Error fetching draws for %s to %s: %s", start_date, end_date, exc)
            return []

    def fetch_year_draws(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all draws for a given year.
        """
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        return self.fetch_draws_range(start_date, end_date)

    def _parse_draw(self, draw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw API draw object into normalized structure.
        """
        try:
            draw_time = draw.get("drawTime")
            if not draw_time:
                return None

            # Μετατροπή timestamp/iso date σε YYYY-MM-DD
            if isinstance(draw_time, (int, float)):
                dt = datetime.fromtimestamp(draw_time / 1000.0)
            else:
                dt = datetime.fromisoformat(str(draw_time).replace("Z", "+00:00"))

            draw_date = dt.strftime("%Y-%m-%d")

            winning = draw.get("winningNumbers", {})
            primary_numbers = sorted(winning.get("list", []))
            
            # Στο Eurojackpot οι 2 αριθμοί Euro επιστρέφονται στο 'bonus'
            euro_numbers = sorted(winning.get("bonus", []))

            # Έλεγχος εγκυρότητας: 5 κύριοι αριθμοί (1-50) & 2 αριθμοί Euro (1-12)
            if len(primary_numbers) != 5 or len(euro_numbers) != 2:
                logger.warning(
                    "Invalid numbers structure for draw %s: primary=%s, euro=%s",
                    draw_date,
                    primary_numbers,
                    euro_numbers,
                )
                return None

            return {
                "draw_date": draw_date,
                "primary_numbers": primary_numbers,
                "euro_numbers": euro_numbers,
            }

        except Exception as exc:
            logger.warning("Failed to parse draw item: %s", exc)
            return None
