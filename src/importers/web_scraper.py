"""
Web Scraper Module for Eurojackpot draws via OPAP API.
"""

from __future__ import annotations

import calendar
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class EurojackpotWebScraper:
    """Scraper to fetch historical Eurojackpot draw results from OPAP API."""

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
        Fetch all draws for a given year by making monthly chunks.
        """
        all_draws: List[Dict[str, Any]] = []
        now = datetime.now()

        for month in range(1, 13):
            if year == now.year and month > now.month:
                break

            last_day = calendar.monthrange(year, month)[1]
            if year == now.year and month == now.month:
                end_day = now.day
            else:
                end_day = last_day

            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{end_day:02d}"

            month_draws = self.fetch_draws_range(start_date, end_date)
            all_draws.extend(month_draws)

        return all_draws

    def _parse_draw(self, draw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw API draw object into normalized structure.
        """
        try:
            draw_time = draw.get("drawTime")
            if not draw_time:
                return None

            if isinstance(draw_time, (int, float)):
                dt = datetime.fromtimestamp(draw_time / 1000.0)
            else:
                dt = datetime.fromisoformat(str(draw_time).replace("Z", "+00:00"))

            draw_date = dt.strftime("%Y-%m-%d")

            winning = draw.get("winningNumbers", {})
            primary_numbers = sorted(winning.get("list", []))

            # Ανάκτηση Euro numbers από όλα τα πιθανά πεδία του API του ΟΠΑΠ
            euro_list = []
            if "sideClassNum" in winning and isinstance(winning["sideClassNum"], list):
                euro_list = winning["sideClassNum"]
            elif "sideClassNumbers" in winning:
                scn = winning["sideClassNumbers"]
                if isinstance(scn, dict):
                    euro_list = scn.get("list", [])
                elif isinstance(scn, list):
                    euro_list = scn
            elif "sideClassList" in winning and isinstance(winning["sideClassList"], list):
                euro_list = winning["sideClassList"]
            elif "bonus" in winning and isinstance(winning["bonus"], list):
                euro_list = winning["bonus"]

            euro_numbers = sorted(euro_list)

            # Επιβεβαίωση δομής (5 κύριοι αριθμοί & 2 αριθμοί Euro)
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
