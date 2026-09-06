"""
Eurojackpot data scraper using the official OPAP API.

The scraper provides:
- Latest completed Eurojackpot draw
- Historical draws by year
- Robust JSON parsing
- Validation of draw structure
- Date normalization
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Project path for standalone execution
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.core.logger import get_logger


logger = get_logger("WebScraper")


class EurojackpotWebScraper:
    """
    Retrieves Eurojackpot results from the OPAP API.

    Eurojackpot game ID:
        5104
    """

    BASE_URL = "https://api.opap.gr/draws/v3.0/5104"

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Lottery-Intelligence-Platform/1.0 "
                    "(educational research project)"
                ),
                "Accept": "application/json",
            }
        )

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------

    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest completed Eurojackpot draw.

        Returns:
            Normalized draw dictionary or None if unavailable.
        """

        url = f"{self.BASE_URL}/last/20"

        try:
            response = self.session.get(
                url,
                params={"status": "results"},
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()

            draws = self._extract_draw_list(data)

            if not draws:
                logger.warning("OPAP returned no completed Eurojackpot draws.")
                return None

            parsed_draws: List[Dict[str, Any]] = []

            for raw_draw in draws:
                parsed = self._parse_draw(raw_draw)

                if parsed is not None:
                    parsed_draws.append(parsed)

            if not parsed_draws:
                logger.warning(
                    "OPAP response contained no valid Eurojackpot draw."
                )
                return None

            latest = max(
                parsed_draws,
                key=lambda draw: draw["draw_date"],
            )

            logger.info(
                "Latest OPAP Eurojackpot draw: %s | Primary=%s | Euro=%s",
                latest["draw_date"],
                latest["primary_numbers"],
                latest["euro_numbers"],
            )

            return latest

        except requests.RequestException as exc:
            logger.error("OPAP API request failed: %s", exc)
            return None

        except ValueError as exc:
            logger.error("Invalid JSON returned by OPAP API: %s", exc)
            return None

        except Exception as exc:
            logger.exception("Unexpected error fetching latest draw: %s", exc)
            return None

    def fetch_year_draws(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all completed Eurojackpot draws for a given year.

        The OPAP API date-range endpoint is queried in small chunks
        to avoid excessively large requests.

        Args:
            year: Four-digit year.

        Returns:
            List of normalized draw dictionaries.
        """

        if not 2000 <= year <= 2100:
            raise ValueError(f"Invalid year: {year}")

        start_date = datetime(year, 1, 1).date()

        if year == datetime.now(timezone.utc).year:
            end_date = datetime.now(timezone.utc).date()
        else:
            end_date = datetime(year, 12, 31).date()

        results: Dict[str, Dict[str, Any]] = {}

        current = start_date

        while current <= end_date:
            chunk_end = min(
                current + timedelta(days=29),
                end_date,
            )

            url = (
                f"{self.BASE_URL}/draw-date/"
                f"{current.isoformat()}/"
                f"{chunk_end.isoformat()}"
            )

            try:
                response = self.session.get(
                    url,
                    params={"status": "results"},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()

                raw_draws = self._extract_draw_list(data)

                for raw_draw in raw_draws:
                    parsed = self._parse_draw(raw_draw)

                    if parsed is None:
                        continue

                    if parsed["draw_date"].startswith(str(year)):
                        results[parsed["draw_date"]] = parsed

                logger.info(
                    "Fetched OPAP period %s -> %s | valid draws=%d",
                    current.isoformat(),
                    chunk_end.isoformat(),
                    len(raw_draws),
                )

            except requests.RequestException as exc:
                logger.warning(
                    "OPAP request failed for %s -> %s: %s",
                    current.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )

            except ValueError as exc:
                logger.warning(
                    "Invalid JSON for %s -> %s: %s",
                    current.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )

            except Exception as exc:
                logger.exception(
                    "Unexpected error for %s -> %s: %s",
                    current.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )

            current = chunk_end + timedelta(days=1)

        draws = sorted(
            results.values(),
            key=lambda draw: draw["draw_date"],
            reverse=True,
        )

        logger.info(
            "Year %d completed | total valid draws=%d",
            year,
            len(draws),
        )

        return draws

    # ---------------------------------------------------------
    # JSON EXTRACTION
    # ---------------------------------------------------------

    @staticmethod
    def _extract_draw_list(data: Any) -> List[Dict[str, Any]]:
        """
        Extract draw objects from different OPAP response structures.
        """

        if isinstance(data, list):
            return [
                item
                for item in data
                if isinstance(item, dict)
            ]

        if not isinstance(data, dict):
            return []

        # Typical paginated response
        content = data.get("content")

        if isinstance(content, list):
            return [
                item
                for item in content
                if isinstance(item, dict)
            ]

        # Possible single-draw response
        for key in ("draw", "lastDraw", "latest"):
            value = data.get(key)

            if isinstance(value, dict):
                return [value]

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

        return []

    # ---------------------------------------------------------
    # DRAW PARSER
    # ---------------------------------------------------------

    def _parse_draw(
        self,
        draw: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Convert an OPAP draw object into the database format.
        """

        try:
            winning = draw.get("winningNumbers", {})

            if not isinstance(winning, dict):
                return None

            primary = winning.get("list", [])

            if not isinstance(primary, list):
                return None

            primary_numbers = [
                int(number)
                for number in primary
            ]

            # OPAP stores Euro numbers in sideLists["1"]["list"]
            euro_numbers: List[int] = []

            side_lists = winning.get("sideLists", {})

            if isinstance(side_lists, dict):
                side_one = side_lists.get("1", {})

                if isinstance(side_one, dict):
                    euro = side_one.get("list", [])

                    if isinstance(euro, list):
                        euro_numbers = [
                            int(number)
                            for number in euro
                        ]

            # Some API structures may use bonus/euro fields
            if not euro_numbers:
                for key in (
                    "bonus",
                    "euroNumbers",
                    "additionalNumbers",
                    "extraNumbers",
                ):
                    value = winning.get(key)

                    if isinstance(value, list):
                        euro_numbers = [
                            int(number)
                            for number in value
                        ]
                        break

            draw_time = draw.get("drawTime")

            draw_date = self._parse_draw_date(draw_time)

            if not draw_date:
                return None

            # Structural validation
            if len(primary_numbers) != 5:
                logger.warning(
                    "Invalid primary numbers for draw %s: %s",
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
                    "Duplicate primary numbers for draw %s",
                    draw_date,
                )
                return None

            if len(set(euro_numbers)) != 2:
                logger.warning(
                    "Duplicate Euro numbers for draw %s",
                    draw_date,
                )
                return None

            if not all(1 <= n <= 50 for n in primary_numbers):
                return None

            if not all(1 <= n <= 12 for n in euro_numbers):
                return None

            return {
                "draw_date": draw_date,
                "primary_numbers": sorted(primary_numbers),
                "euro_numbers": sorted(euro_numbers),
            }

        except (TypeError, ValueError, KeyError) as exc:
            logger.warning(
                "Could not parse OPAP draw: %s",
                exc,
            )
            return None

    # ---------------------------------------------------------
    # DATE HANDLING
    # ---------------------------------------------------------

    @staticmethod
    def _parse_draw_date(value: Any) -> Optional[str]:
        """
        Convert OPAP drawTime to YYYY-MM-DD.

        OPAP normally returns Unix timestamp in milliseconds.
        """

        if value is None:
            return None

        try:
            if isinstance(value, (int, float)):
                timestamp = float(value)

                # OPAP uses milliseconds.
                if timestamp > 10_000_000_000:
                    timestamp /= 1000.0

                dt = datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                )

                return dt.strftime("%Y-%m-%d")

            if isinstance(value, str):
                text = value.strip()

                if not text:
                    return None

                # ISO datetime
                if "T" in text:
                    text = text.split("T")[0]

                for fmt in (
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                    "%m/%d/%Y",
                    "%d.%m.%Y",
                    "%Y/%m/%d",
                ):
                    try:
                        return datetime.strptime(
                            text,
                            fmt,
                        ).strftime("%Y-%m-%d")
                    except ValueError:
                        continue

        except (TypeError, ValueError, OSError) as exc:
            logger.warning(
                "Could not normalize draw date %r: %s",
                value,
                exc,
            )

        return None


if __name__ == "__main__":
    scraper = EurojackpotWebScraper()

    latest = scraper.fetch_latest_draw()

    if latest:
        print(
            f"{latest['draw_date']} | "
            f"{latest['primary_numbers']} | "
            f"{latest['euro_numbers']}"
        )
    else:
        print("No draw retrieved.")
