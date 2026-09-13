"""
Eurojackpot Web Scraper.

Uses the official OPAP API to retrieve Eurojackpot results.

The scraper provides:
- latest draw
- draws for a date range
- historical draws by year
- strict validation of 5 main + 2 Euro numbers

OPAP Eurojackpot game ID: 5109
"""

from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


class EurojackpotWebScraper:
    """Retrieve Eurojackpot draws from the official OPAP API."""

    GAME_ID = 5109
    BASE_URL = f"https://api.opap.gr/draws/v3.0/{GAME_ID}"

    REQUEST_TIMEOUT = 30

    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest available Eurojackpot draw.

        Returns:
            Normalized draw dictionary or None if unavailable.
        """
        url = f"{self.BASE_URL}/last-results"

        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            # OPAP normally returns a list for /last-results.
            if isinstance(data, list):
                if not data:
                    logger.warning("OPAP returned an empty latest-results list.")
                    return None

                # Normally the first item is the latest draw.
                candidates = data

            elif isinstance(data, dict):
                candidates = data.get("content", [])

                if not candidates:
                    # Some API responses may contain the draw directly.
                    candidates = [data]

            else:
                logger.error(
                    "Unexpected OPAP latest-results response type: %s",
                    type(data).__name__,
                )
                return None

            parsed_draws: List[Dict[str, Any]] = []

            for raw_draw in candidates:
                parsed = self._parse_draw(raw_draw)

                if parsed is not None:
                    parsed_draws.append(parsed)

            if not parsed_draws:
                logger.error(
                    "OPAP returned latest draw data, but no valid "
                    "Eurojackpot draw could be parsed."
                )
                return None

            parsed_draws.sort(
                key=lambda draw: draw["draw_date"],
                reverse=True,
            )

            latest = parsed_draws[0]

            logger.info(
                "Latest OPAP draw: %s | Main=%s | Euro=%s",
                latest["draw_date"],
                latest["primary_numbers"],
                latest["euro_numbers"],
            )

            return latest

        except requests.RequestException as exc:
            logger.error(
                "Failed to retrieve latest Eurojackpot draw from OPAP: %s",
                exc,
            )
            return None

        except ValueError as exc:
            logger.error(
                "Invalid JSON received from OPAP latest-results endpoint: %s",
                exc,
            )
            return None

        except Exception:
            logger.exception(
                "Unexpected error while retrieving latest Eurojackpot draw."
            )
            return None

    def fetch_draws_range(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch Eurojackpot draws between two dates.

        Dates must use:
            YYYY-MM-DD
        """
        url = (
            f"{self.BASE_URL}/draw-date/"
            f"{start_date}/{end_date}"
        )

        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict):
                raw_draws = data.get("content", [])
            elif isinstance(data, list):
                raw_draws = data
            else:
                logger.error(
                    "Unexpected OPAP response type for %s - %s: %s",
                    start_date,
                    end_date,
                    type(data).__name__,
                )
                return []

            parsed_draws: List[Dict[str, Any]] = []

            for raw_draw in raw_draws:
                parsed = self._parse_draw(raw_draw)

                if parsed is not None:
                    parsed_draws.append(parsed)

            parsed_draws.sort(
                key=lambda draw: draw["draw_date"]
            )

            logger.info(
                "OPAP range %s to %s: %d valid draws",
                start_date,
                end_date,
                len(parsed_draws),
            )

            return parsed_draws

        except requests.RequestException as exc:
            logger.error(
                "OPAP request failed for %s - %s: %s",
                start_date,
                end_date,
                exc,
            )
            return []

        except ValueError as exc:
            logger.error(
                "Invalid JSON from OPAP for %s - %s: %s",
                start_date,
                end_date,
                exc,
            )
            return []

        except Exception:
            logger.exception(
                "Unexpected error fetching OPAP range %s - %s",
                start_date,
                end_date,
            )
            return []

    def fetch_year_draws(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all available Eurojackpot draws for a given year.

        The year is divided into monthly requests to keep each API
        request reasonably small.
        """
        today = datetime.now(timezone.utc).date()

        if year < 2012:
            logger.warning(
                "Eurojackpot did not exist before 2012. "
                "Skipping year %s.",
                year,
            )
            return []

        if year > today.year:
            logger.warning(
                "Year %s is in the future. Skipping.",
                year,
            )
            return []

        all_draws: Dict[str, Dict[str, Any]] = {}

        last_month = 12

        if year == today.year:
            last_month = today.month

        for month in range(1, last_month + 1):
            first_day = f"{year:04d}-{month:02d}-01"

            last_day_number = calendar.monthrange(
                year,
                month,
            )[1]

            if year == today.year and month == today.month:
                last_day_number = today.day

            last_day = (
                f"{year:04d}-{month:02d}-{last_day_number:02d}"
            )

            logger.info(
                "Fetching Eurojackpot draws for %s",
                f"{year:04d}-{month:02d}",
            )

            monthly_draws = self.fetch_draws_range(
                first_day,
                last_day,
            )

            for draw in monthly_draws:
                all_draws[draw["draw_date"]] = draw

        result = sorted(
            all_draws.values(),
            key=lambda draw: draw["draw_date"],
        )

        logger.info(
            "Year %s completed: %d valid draws",
            year,
            len(result),
        )

        return result

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_draw(
        self,
        draw: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert one raw OPAP draw into the project's standard format.

        Required result:
            5 main numbers from 1-50
            2 Euro numbers from 1-12
        """
        if not isinstance(draw, dict):
            logger.warning(
                "Skipping non-dictionary OPAP draw."
            )
            return None

        draw_time = draw.get("drawTime")

        if draw_time is None:
            logger.warning(
                "Skipping OPAP draw without drawTime."
            )
            return None

        draw_datetime = self._parse_draw_datetime(draw_time)

        if draw_datetime is None:
            logger.warning(
                "Skipping OPAP draw with invalid drawTime: %r",
                draw_time,
            )
            return None

        draw_date = draw_datetime.strftime("%Y-%m-%d")

        winning_numbers = draw.get("winningNumbers")

        if not isinstance(winning_numbers, dict):
            logger.warning(
                "Skipping draw %s: missing winningNumbers.",
                draw_date,
            )
            return None

        # --------------------------------------------------------------
        # Main numbers
        # --------------------------------------------------------------

        primary_numbers = self._extract_primary_numbers(
            winning_numbers
        )

        # --------------------------------------------------------------
        # Euro numbers
        # --------------------------------------------------------------

        euro_numbers = self._extract_euro_numbers(
            winning_numbers
        )

        # --------------------------------------------------------------
        # Strict validation
        # --------------------------------------------------------------

        if len(primary_numbers) != 5:
            logger.warning(
                "Invalid main numbers for draw %s: %s",
                draw_date,
                primary_numbers,
            )
            return None

        if len(euro_numbers) != 2:
            logger.warning(
                "Invalid Euro numbers for draw %s: %s",
                draw_date,
                euro_numbers,
            )
            return None

        if len(set(primary_numbers)) != 5:
            logger.warning(
                "Duplicate main numbers for draw %s: %s",
                draw_date,
                primary_numbers,
            )
            return None

        if len(set(euro_numbers)) != 2:
            logger.warning(
                "Duplicate Euro numbers for draw %s: %s",
                draw_date,
                euro_numbers,
            )
            return None

        if not all(1 <= number <= 50 for number in primary_numbers):
            logger.warning(
                "Main number outside 1-50 for draw %s: %s",
                draw_date,
                primary_numbers,
            )
            return None

        if not all(1 <= number <= 12 for number in euro_numbers):
            logger.warning(
                "Euro number outside 1-12 for draw %s: %s",
                draw_date,
                euro_numbers,
            )
            return None

        return {
            "draw_date": draw_date,
            "primary_numbers": sorted(primary_numbers),
            "euro_numbers": sorted(euro_numbers),
        }

    # ------------------------------------------------------------------
    # OPAP number extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_primary_numbers(
        winning_numbers: Dict[str, Any],
    ) -> List[int]:
        """Extract the five main Eurojackpot numbers."""
        value = winning_numbers.get("list")

        if not isinstance(value, list):
            return []

        numbers: List[int] = []

        for item in value:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue

            if 1 <= number <= 50:
                numbers.append(number)

        return sorted(numbers)

    @staticmethod
    def _extract_euro_numbers(
        winning_numbers: Dict[str, Any],
    ) -> List[int]:
        """
        Extract the two Euro numbers.

        OPAP has used different field names in API responses over time,
        so the parser checks the known structures in a safe order.
        """
        possible_fields = (
            "sideClassNum",
            "sideClassNumbers",
            "sideClassList",
            "bonus",
        )

        for field_name in possible_fields:
            value = winning_numbers.get(field_name)

            if value is None:
                continue

            values: List[Any] = []

            if isinstance(value, dict):
                sub_list = value.get("list")
                if isinstance(sub_list, list):
                    values = sub_list
            elif isinstance(value, list):
                values = value
            else:
                values = [value]

            numbers: List[int] = []

            for item in values:
                try:
                    number = int(item)
                except (TypeError, ValueError):
                    continue

                if 1 <= number <= 12:
                    numbers.append(number)

            if len(numbers) >= 2:
                return sorted(numbers[:2])

        return []

    # ------------------------------------------------------------------
    # Date handling
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_draw_datetime(
        draw_time: Any,
    ) -> Optional[datetime]:
        """Convert an OPAP drawTime value into a timezone-aware datetime."""

        try:
            # OPAP normally provides milliseconds since Unix epoch.
            if isinstance(draw_time, (int, float)):
                return datetime.fromtimestamp(
                    draw_time / 1000.0,
                    tz=timezone.utc,
                )

            if isinstance(draw_time, str):
                value = draw_time.strip()

                if not value:
                    return None

                # Numeric timestamp supplied as a string.
                if value.isdigit():
                    timestamp = int(value)

                    # Milliseconds are expected. This also protects
                    # against accidental second-based timestamps.
                    if timestamp > 10_000_000_000:
                        timestamp_seconds = timestamp / 1000.0
                    else:
                        timestamp_seconds = float(timestamp)

                    return datetime.fromtimestamp(
                        timestamp_seconds,
                        tz=timezone.utc,
                    )

                # ISO 8601 timestamp.
                normalized = value.replace("Z", "+00:00")

                parsed = datetime.fromisoformat(normalized)

                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)

                return parsed.astimezone(timezone.utc)

        except (TypeError, ValueError, OverflowError, OSError):
            return None

        return None
