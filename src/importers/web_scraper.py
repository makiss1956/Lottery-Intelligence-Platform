"""
Eurojackpot Web Scraper.

Uses the official OPAP API to retrieve Eurojackpot results.
Supports:
- latest draw
- historical draws by year
- correct OPAP JSON parsing
- validation of 5 main + 2 Euro numbers
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

try:
    from src.core.logger import get_logger
    logger = get_logger("WebScraper")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("WebScraper")


class EurojackpotWebScraper:
    """Retrieve Eurojackpot results from the official OPAP API."""

    GAME_ID = 5104
    BASE_URL = f"https://api.opap.gr/draws/v3.0/{GAME_ID}"

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Lottery-Intelligence-Platform/1.0",
                "Accept": "application/json",
            }
        )

    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest completed Eurojackpot draw."""
        url = f"{self.BASE_URL}/last/20"

        try:
            response = self.session.get(
                url,
                params={"status": "results"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            draws = self._extract_draws(data)
            parsed_draws: List[Dict[str, Any]] = []

            for raw_draw in draws:
                parsed = self._parse_draw(raw_draw)
                if parsed is not None:
                    parsed_draws.append(parsed)

            if not parsed_draws:
                logger.error("OPAP returned no valid Eurojackpot draw.")
                return None

            latest = max(
                parsed_draws,
                key=lambda item: item["draw_date"],
            )

            logger.info(
                "Latest draw: %s | Main=%s | Euro=%s",
                latest["draw_date"],
                latest["primary_numbers"],
                latest["euro_numbers"],
            )

            return latest

        except requests.RequestException as exc:
            logger.error("OPAP request failed: %s", exc)
            return None
        except ValueError as exc:
            logger.error("Invalid JSON from OPAP: %s", exc)
            return None
        except Exception as exc:
            logger.exception("Unexpected error fetching latest draw: %s", exc)
            return None

    def fetch_year_draws(self, year: int) -> List[Dict[str, Any]]:
        """Fetch all Eurojackpot draws for a given year."""
        if year < 2012 or year > 2100:
            raise ValueError(f"Invalid Eurojackpot year: {year}")

        start_date = datetime(year, 1, 1).date()
        current_year = datetime.now().year

        if year == current_year:
            end_date = datetime.now().date()
        else:
            end_date = datetime(year, 12, 31).date()

        draws_by_date: Dict[str, Dict[str, Any]] = {}
        current_date = start_date

        while current_date <= end_date:
            chunk_end = min(
                current_date + timedelta(days=29),
                end_date,
            )

            url = (
                f"{self.BASE_URL}/draw-date/"
                f"{current_date.isoformat()}/"
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

                raw_draws = self._extract_draws(data)
                valid_in_chunk = 0

                for raw_draw in raw_draws:
                    parsed = self._parse_draw(raw_draw)
                    if parsed is None:
                        continue

                    if not parsed["draw_date"].startswith(str(year)):
                        continue

                    draws_by_date[parsed["draw_date"]] = parsed
                    valid_in_chunk += 1

                logger.info(
                    "Fetched OPAP period %s -> %s | valid draws=%d",
                    current_date.isoformat(),
                    chunk_end.isoformat(),
                    valid_in_chunk,
                )

            except requests.RequestException as exc:
                logger.warning(
                    "OPAP request failed for %s -> %s: %s",
                    current_date.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )
            except ValueError as exc:
                logger.warning(
                    "Invalid JSON for %s -> %s: %s",
                    current_date.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )
            except Exception as exc:
                logger.exception(
                    "Unexpected error for %s -> %s: %s",
                    current_date.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )

            current_date = chunk_end + timedelta(days=1)

        result = sorted(
            draws_by_date.values(),
            key=lambda item: item["draw_date"],
        )

        logger.info(
            "Year %d completed | total valid draws=%d",
            year,
            len(result),
        )

        return result

    @staticmethod
    def _extract_draws(data: Any) -> List[Dict[str, Any]]:
        """Extract draw objects from OPAP responses."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if not isinstance(data, dict):
            return []

        content = data.get("content")
        if isinstance(content, list):
            return [item for item in content if isinstance(item, dict)]

        for key in ("last", "lastDraw", "latest", "draw"):
            value = data.get(key)
            if isinstance(value, dict):
                return [value]
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        return []

    def _parse_draw(self, draw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse one OPAP draw."""
        try:
            winning = draw.get("winningNumbers", {})
            if not isinstance(winning, dict):
                return None

            primary_raw = winning.get("list", [])
            if not isinstance(primary_raw, list):
                return None

            primary_numbers = [int(number) for number in primary_raw]

            euro_raw = winning.get("bonus", [])
            if not isinstance(euro_raw, list):
                euro_raw = []

            euro_numbers = [int(number) for number in euro_raw]

            if len(euro_numbers) != 2:
                for key in ("euroNumbers", "additionalNumbers", "extraNumbers"):
                    alternative = winning.get(key)
                    if isinstance(alternative, list) and len(alternative) == 2:
                        euro_numbers = [int(number) for number in alternative]
                        break

            draw_date = self._parse_draw_date(draw.get("drawTime"))
            if draw_date is None:
                draw_date = self._parse_draw_date(draw.get("drawDate"))

            if draw_date is None:
                return None

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

            if len(set(primary_numbers)) != 5 or len(set(euro_numbers)) != 2:
                return None

            if not all(1 <= number <= 50 for number in primary_numbers):
                return None

            if not all(1 <= number <= 12 for number in euro_numbers):
                return None

            return {
                "draw_date": draw_date,
                "primary_numbers": sorted(primary_numbers),
                "euro_numbers": sorted(euro_numbers),
            }

        except (TypeError, ValueError, KeyError) as exc:
            logger.warning("Could not parse draw: %s", exc)
            return None

    @staticmethod
    def _parse_draw_date(value: Any) -> Optional[str]:
        """Convert OPAP date/time to YYYY-MM-DD."""
        if value is None:
            return None

        try:
            if isinstance(value, (int, float)):
                timestamp = float(value)
                if timestamp > 10_000_000_000:
                    timestamp /= 1000.0

                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                return dt.strftime("%Y-%m-%d")

            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return None

                if "T" in text:
                    text = text.split("T", 1)[0]

                formats = (
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                    "%m/%d/%Y",
                    "%d.%m.%Y",
                    "%Y/%m/%d",
                )

                for fmt in formats:
                    try:
                        return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        continue

        except (TypeError, ValueError, OSError) as exc:
            logger.warning("Date conversion failed for %r: %s", value, exc)

        return None


if __name__ == "__main__":
    scraper = EurojackpotWebScraper()
    latest = scraper.fetch_latest_draw()

    if latest:
        print("Latest Eurojackpot draw:")
        print(f"Date: {latest['draw_date']}")
        print(f"Main: {latest['primary_numbers']}")
        print(f"Euro: {latest['euro_numbers']}")
    else:
        print("No Eurojackpot draw retrieved.")
