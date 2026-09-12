"""
Eurojackpot Data Importer.

Coordinates:
- historical CSV data
- SQLite database
- official OPAP API

The importer keeps the database synchronized and uses the OPAP API
as the authoritative fallback when the CSV does not contain the
latest draw.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from src.core.logger import get_logger


logger = get_logger("EurojackpotImporter")


class EurojackpotImporter:
    """Import and synchronize Eurojackpot draw data."""

    CSV_FILENAME = "eurojackpot_raw_history.csv"

    def __init__(self, db_manager=None) -> None:
        self.db_manager = db_manager

        base_dir = Path(__file__).resolve().parent.parent.parent
        self.base_dir = base_dir
        self.csv_path = base_dir / "data" / self.CSV_FILENAME

    # ------------------------------------------------------------------
    # Latest draw
    # ------------------------------------------------------------------

    def get_latest_draw(self) -> Optional[Dict[str, Any]]:
        """
        Return the latest known draw.

        Priority:
        1. Official OPAP API
        2. CSV
        3. SQLite database

        The API is checked first so that a newer draw cannot be hidden
        simply because the CSV has not yet been updated.
        """
        api_draw = self._fetch_latest_from_opap()

        if api_draw is not None:
            if self.db_manager is not None:
                self._store_draw(api_draw)

            return api_draw

        logger.warning(
            "OPAP latest draw unavailable. Trying CSV/database fallback."
        )

        csv_draw = self._fetch_latest_from_csv()

        if csv_draw is not None:
            if self.db_manager is not None:
                self._store_draw(csv_draw)

            return csv_draw

        if self.db_manager is not None:
            db_draw = self.db_manager.get_latest_draw()

            if db_draw is not None:
                logger.warning(
                    "Using latest draw from SQLite: %s",
                    db_draw["draw_date"],
                )
                return db_draw

        logger.error("No latest Eurojackpot draw is available.")

        return None

    # Backward-compatible alias.
    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """Backward-compatible alias for get_latest_draw()."""
        return self.get_latest_draw()

    # ------------------------------------------------------------------
    # History synchronization
    # ------------------------------------------------------------------

    def sync_history(self) -> int:
        """
        Synchronize CSV history and the latest OPAP draw into SQLite.

        Returns:
            Number of newly inserted draws.

        Raises:
            RuntimeError if there is no usable source data and the
            database is empty.
        """
        if self.db_manager is None:
            raise RuntimeError(
                "DBManager is required for history synchronization."
            )

        inserted_count = 0
        valid_csv_count = 0

        # --------------------------------------------------------------
        # 1. Import valid CSV rows.
        # --------------------------------------------------------------

        rows = self._read_csv_rows()

        for row in rows:
            draw = self._parse_row(row)

            if draw is None:
                continue

            valid_csv_count += 1

            if self._store_draw(draw):
                inserted_count += 1

        logger.info(
            "CSV synchronization complete: %d valid rows, %d new draws.",
            valid_csv_count,
            inserted_count,
        )

        # --------------------------------------------------------------
        # 2. Always check the official OPAP API for the latest draw.
        # --------------------------------------------------------------

        latest_api_draw = self._fetch_latest_from_opap()

        if latest_api_draw is not None:
            if self._store_draw(latest_api_draw):
                inserted_count += 1

            logger.info(
                "Latest OPAP draw synchronized: %s",
                latest_api_draw["draw_date"],
            )

        else:
            logger.warning(
                "Could not retrieve the latest draw from OPAP during "
                "history synchronization."
            )

        # --------------------------------------------------------------
        # 3. Safety check.
        # --------------------------------------------------------------

        db_count = self.db_manager.get_draw_count()

        if db_count == 0:
            raise RuntimeError(
                "History synchronization failed: SQLite contains "
                "zero draws after CSV and OPAP synchronization."
            )

        logger.info(
            "Database synchronization finished: %d total draws, "
            "%d newly inserted.",
            db_count,
            inserted_count,
        )

        return inserted_count

    # ------------------------------------------------------------------
    # Draw storage
    # ------------------------------------------------------------------

    def _store_draw(self, draw: Dict[str, Any]) -> bool:
        """
        Store one draw.

        If the same date already exists with different numbers, the
        existing row is replaced. This protects the database from
        stale or previously incorrect data.
        """
        if self.db_manager is None:
            return False

        draw_date = draw["draw_date"]

        existing = self.db_manager.get_draw(draw_date)

        if existing is None:
            inserted = self.db_manager.insert_draw(draw)

            if inserted:
                logger.info(
                    "Inserted draw %s: Main=%s Euro=%s",
                    draw_date,
                    draw["primary_numbers"],
                    draw["euro_numbers"],
                )

            return inserted

        same_main = (
            sorted(existing.get("primary_numbers", []))
            == sorted(draw.get("primary_numbers", []))
        )

        same_euro = (
            sorted(existing.get("euro_numbers", []))
            == sorted(draw.get("euro_numbers", []))
        )

        if same_main and same_euro:
            return False

        logger.warning(
            "Correcting existing draw %s. Old=%s + %s, New=%s + %s",
            draw_date,
            existing.get("primary_numbers"),
            existing.get("euro_numbers"),
            draw["primary_numbers"],
            draw["euro_numbers"],
        )

        return self.db_manager.replace_draw(draw)

    # ------------------------------------------------------------------
    # OPAP API
    # ------------------------------------------------------------------

    def _fetch_latest_from_opap(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest draw from the official OPAP API."""
        try:
            from src.importers.web_scraper import EurojackpotWebScraper

            scraper = EurojackpotWebScraper()
            draw = scraper.fetch_latest_draw()

            if draw is not None:
                logger.info(
                    "OPAP latest draw received: %s",
                    draw["draw_date"],
                )

            return draw

        except Exception:
            logger.exception(
                "Unexpected error while fetching latest draw from OPAP."
            )
            return None

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def _read_csv_rows(self) -> List[Dict[str, str]]:
        """Read the project's historical CSV file."""
        if not self.csv_path.exists():
            logger.warning(
                "Historical CSV does not exist: %s",
                self.csv_path,
            )
            return []

        try:
            with self.csv_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                reader = csv.DictReader(
                    csv_file,
                    delimiter=";",
                )

                rows = list(reader)

                logger.info(
                    "Read %d rows from %s",
                    len(rows),
                    self.csv_path,
                )

                return rows

        except OSError as exc:
            logger.error(
                "Unable to read historical CSV %s: %s",
                self.csv_path,
                exc,
            )
            return []

        except csv.Error as exc:
            logger.error(
                "Invalid CSV format in %s: %s",
                self.csv_path,
                exc,
            )
            return []

    def _fetch_latest_from_csv(
        self,
    ) -> Optional[Dict[str, Any]]:
        """Return the newest valid draw from the CSV."""
        rows = self._read_csv_rows()

        latest_draw: Optional[Dict[str, Any]] = None

        for row in rows:
            draw = self._parse_row(row)

            if draw is None:
                continue

            if (
                latest_draw is None
                or draw["draw_date"] > latest_draw["draw_date"]
            ):
                latest_draw = draw

        if latest_draw is not None:
            logger.info(
                "Latest valid CSV draw: %s",
                latest_draw["draw_date"],
            )

        return latest_draw

    def _parse_row(
        self,
        row: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Parse and validate one CSV row."""
        if not row:
            return None

        date_value = (
            row.get("Date")
            or row.get("date")
            or row.get("draw_date")
        )

        if not date_value:
            return None

        draw_date = self._normalize_csv_date(str(date_value))

        if draw_date is None:
            logger.warning(
                "Skipping CSV row with invalid date: %r",
                date_value,
            )
            return None

        try:
            primary_numbers = [
                int(row.get(f"N{i}", ""))
                for i in range(1, 6)
            ]

            euro_numbers = [
                int(row.get(f"E{i}", ""))
                for i in range(1, 3)
            ]

        except (TypeError, ValueError):
            logger.warning(
                "Skipping CSV row %s: invalid number fields.",
                draw_date,
            )
            return None

        # Strict validation of main numbers.
        if len(primary_numbers) != 5:
            return None

        if len(set(primary_numbers)) != 5:
            logger.warning(
                "Skipping %s: duplicate main numbers %s",
                draw_date,
                primary_numbers,
            )
            return None

        if not all(1 <= number <= 50 for number in primary_numbers):
            logger.warning(
                "Skipping %s: main number outside 1-50: %s",
                draw_date,
                primary_numbers,
            )
            return None

        # Strict validation of Euro numbers.
        if len(euro_numbers) != 2:
            return None

        if len(set(euro_numbers)) != 2:
            logger.warning(
                "Skipping %s: duplicate Euro numbers %s",
                draw_date,
                euro_numbers,
            )
            return None

        if not all(1 <= number <= 12 for number in euro_numbers):
            logger.warning(
                "Skipping %s: Euro number outside 1-12: %s",
                draw_date,
                euro_numbers,
            )
            return None

        return {
            "draw_date": draw_date,
            "primary_numbers": sorted(primary_numbers),
            "euro_numbers": sorted(euro_numbers),
        }

    @staticmethod
    def _normalize_csv_date(
        value: str,
    ) -> Optional[str]:
        """Normalize supported CSV date formats to YYYY-MM-DD."""
        value = value.strip()

        if not value:
            return None

        formats = (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
        )

        for date_format in formats:
            try:
                parsed = datetime.strptime(
                    value,
                    date_format,
                )
                return parsed.strftime("%Y-%m-%d")

            except ValueError:
                continue

        # Handle ISO timestamps such as:
        # 2026-08-20T21:00:00
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
            return parsed.strftime("%Y-%m-%d")

        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Next draw date
    # ------------------------------------------------------------------

    def get_next_draw_date(self) -> str:
        """
        Calculate the next expected Eurojackpot draw date.

        Eurojackpot draws are Tuesday and Friday.

        Greece time is used so that daylight-saving changes are handled
        correctly instead of relying on a fixed UTC+2 offset.
        """
        greece_tz = ZoneInfo("Europe/Athens")

        now = datetime.now(greece_tz)

        # Eurojackpot draw days:
        # Monday=0, Tuesday=1, Wednesday=2, Thursday=3,
        # Friday=4, Saturday=5, Sunday=6.
        draw_weekdays = {1, 4}

        today = now.date()

        for days_ahead in range(0, 8):
            candidate = today + timedelta(days=days_ahead)

            if candidate.weekday() not in draw_weekdays:
                continue

            # Expected draw time is approximately 21:00 Greece time.
            # On the draw day, if we are already past 21:00,
            # move to the next draw day.
            candidate_datetime = datetime(
                candidate.year,
                candidate.month,
                candidate.day,
                21,
                0,
                tzinfo=greece_tz,
            )

            if candidate_datetime > now:
                return candidate.strftime("%Y-%m-%d")

        # This should never normally be reached.
        fallback = today + timedelta(days=7)
        return fallback.strftime("%Y-%m-%d")
