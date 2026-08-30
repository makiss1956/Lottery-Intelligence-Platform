"""
Eurojackpot Data Importer.

CSV is the primary source.
The importer synchronizes all valid CSV rows
into the SQLite database using idempotent inserts.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger


logger = get_logger("EurojackpotImporter")


class EurojackpotImporter:
    """Import Eurojackpot draws from the local CSV file."""

    def __init__(self, db_manager=None) -> None:
        self.db_manager = db_manager

        base_dir = Path(__file__).resolve().parent.parent.parent

        self.csv_path = (
            base_dir / "data" / "eurojackpot_raw_history.csv"
        )

    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """Read the latest draw from CSV, fallback to web scraper."""
        result = self._fetch_from_csv()
        if result:
            return result

        # Fallback: try web scraper
        logger.info("CSV empty or outdated. Trying web scraper...")
        from src.importers.web_scraper import EurojackpotWebScraper
        scraper = EurojackpotWebScraper()
        return scraper.fetch_latest_draw()

    def _read_csv_rows(self) -> List[Dict[str, str]]:
        """Read all CSV rows."""

        if not self.csv_path.exists():
            logger.error(
                "CSV not found: %s",
                self.csv_path,
            )
            return []

        try:
            with self.csv_path.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as file:

                reader = csv.DictReader(
                    file,
                    delimiter=";",
                )

                return list(reader)

        except Exception as exc:
            logger.error(
                "CSV read failed: %s",
                exc,
            )
            return []

    @staticmethod
    def _parse_row(
        row: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Convert one CSV row to normalized draw data."""

        date_str = row.get(
            "Date",
            "",
        ).strip()

        if not date_str or date_str == "YYYY-MM-DD":
            return None

        primary: List[int] = []
        euro: List[int] = []

        for index in range(1, 6):
            value = row.get(
                f"N{index}",
                "",
            ).strip()

            if not value.isdigit():
                return None

            number = int(value)

            if not 1 <= number <= 50:
                return None

            primary.append(number)

        for index in range(1, 3):
            value = row.get(
                f"E{index}",
                "",
            ).strip()

            if not value.isdigit():
                return None

            number = int(value)

            if not 1 <= number <= 12:
                return None

            euro.append(number)

        if len(set(primary)) != 5:
            return None

        if len(set(euro)) != 2:
            return None

        return {
            "draw_date": date_str,
            "primary_numbers": sorted(primary),
            "euro_numbers": sorted(euro),
        }

    def _fetch_from_csv(
        self,
    ) -> Optional[Dict[str, Any]]:
        """Return the newest valid CSV draw."""

        rows = self._read_csv_rows()

        if not rows:
            logger.warning(
                "CSV contains no rows."
            )
            return None

        draws: List[Dict[str, Any]] = []

        for row in rows:
            draw = self._parse_row(row)

            if draw is not None:
                draws.append(draw)

        if not draws:
            logger.warning(
                "No valid draws found in CSV."
            )
            return None

        latest = max(
            draws,
            key=lambda draw: draw["draw_date"],
        )

        logger.info(
            "Latest CSV draw: %s",
            latest["draw_date"],
        )

        return latest

    def sync_history(self) -> int:
        """
        Synchronize ALL valid CSV rows with database.

        Existing draws are ignored.
        New draws are inserted.

        Returns:
            Number of newly inserted draws.
        """

        if self.db_manager is None:
            logger.error(
                "Database manager not configured."
            )
            return 0

        rows = self._read_csv_rows()

        if not rows:
            return 0

        inserted_count = 0
        valid_count = 0

        for row in rows:
            draw = self._parse_row(row)

            if draw is None:
                continue

            valid_count += 1

            if self.db_manager.insert_draw(draw):
                inserted_count += 1

        logger.info(
            "CSV sync complete | "
            "Valid=%d | New=%d",
            valid_count,
            inserted_count,
        )

        return inserted_count

    def get_next_draw_date(self) -> str:
        """
        Return next Eurojackpot draw date.

        Eurojackpot draws are normally Tuesday and Friday.
        """

        today = datetime.now()

        weekday = today.weekday()

        # Tuesday
        if weekday == 1:
            return today.strftime("%Y-%m-%d")

        # Friday
        if weekday == 4:
            return today.strftime("%Y-%m-%d")

        for days_ahead in range(1, 8):
            candidate = (
                today + timedelta(days=days_ahead)
            )

            if candidate.weekday() in (1, 4):
                return candidate.strftime(
                    "%Y-%m-%d"
                )

        # Defensive fallback
        return (
            today + timedelta(days=3)
        ).strftime("%Y-%m-%d")
