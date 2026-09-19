
"""
Eurojackpot importer.

Priority:
1. Official OPAP API for the latest draw.
2. Local CSV as fallback.
3. CSV synchronization into SQLite.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger

logger = get_logger("EurojackpotImporter")


class EurojackpotImporter:

    def __init__(
        self,
        db_manager=None,
    ) -> None:

        self.db_manager = db_manager

        base_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            .parent
        )

        self.csv_path = (
            base_dir
            / "data"
            / "eurojackpot_raw_history.csv"
        )

    # ---------------------------------------------------------
    # Latest draw
    # ---------------------------------------------------------

    def fetch_latest_draw(
        self,
    ) -> Optional[Dict[str, Any]]:

        # IMPORTANT:
        # Try the official OPAP API FIRST.

        try:

            from src.importers.web_scraper import (
                EurojackpotWebScraper,
            )

            scraper = EurojackpotWebScraper()

            latest = scraper.fetch_latest_draw()

            if latest:

                logger.info(
                    "LIVE OPAP draw received: %s",
                    latest["draw_date"],
                )

                # Store immediately.

                if self.db_manager:

                    existing = self.db_manager.get_draw(
                        latest["draw_date"]
                    )

                    if existing is None:

                        self.db_manager.insert_draw(
                            latest
                        )

                    elif existing != latest:

                        self.db_manager.replace_draw(
                            latest
                        )

                return latest

        except Exception:

            logger.exception(
                "Live OPAP retrieval failed. "
                "Falling back to CSV."
            )

        # -----------------------------------------------------
        # CSV fallback
        # -----------------------------------------------------

        logger.warning(
            "Using CSV fallback for latest draw."
        )

        return self._fetch_from_csv()

    # ---------------------------------------------------------
    # CSV
    # ---------------------------------------------------------

    def _read_csv_rows(
        self,
    ) -> List[Dict[str, str]]:

        if not self.csv_path.exists():

            logger.error(
                "CSV file not found: %s",
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
    def _normalize_date(
        value: str,
    ) -> Optional[str]:

        value = value.strip()

        for fmt in (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d.%m.%Y",
        ):

            try:

                return datetime.strptime(
                    value,
                    fmt,
                ).strftime("%Y-%m-%d")

            except ValueError:
                continue

        return None

    @classmethod
    def _parse_row(
        cls,
        row: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:

        draw_date = cls._normalize_date(
            row.get("Date", "")
        )

        if not draw_date:
            return None

        primary = []
        euro = []

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
            "draw_date": draw_date,
            "primary_numbers": sorted(primary),
            "euro_numbers": sorted(euro),
        }

    def _fetch_from_csv(
        self,
    ) -> Optional[Dict[str, Any]]:

        rows = self._read_csv_rows()

        draws = []

        for row in rows:

            draw = self._parse_row(row)

            if draw:
                draws.append(draw)

        if not draws:
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

    # ---------------------------------------------------------
    # Synchronize CSV into database
    # ---------------------------------------------------------

    def sync_history(self) -> int:

        if self.db_manager is None:
            return 0

        rows = self._read_csv_rows()

        inserted = 0

        for row in rows:

            draw = self._parse_row(row)

            if not draw:
                continue

            existing = self.db_manager.get_draw(
                draw["draw_date"]
            )

            if existing is None:

                if self.db_manager.insert_draw(draw):
                    inserted += 1

            elif existing != draw:

                self.db_manager.replace_draw(
                    draw
                )

        logger.info(
            "CSV history synchronization completed. "
            "New draws=%d",
            inserted,
        )

        return inserted

    # ---------------------------------------------------------
    # Next draw
    # ---------------------------------------------------------

    def get_next_draw_date(self) -> str:

        today = datetime.utcnow().date()

        weekday = today.weekday()

        # Tuesday = 1
        # Friday = 4

        if weekday == 1:
            return (
                today + timedelta(days=3)
            ).strftime("%Y-%m-%d")

        if weekday == 4:
            return (
                today + timedelta(days=4)
            ).strftime("%Y-%m-%d")

        for days_ahead in range(1, 8):

            candidate = (
                today
                + timedelta(days=days_ahead)
            )

            if candidate.weekday() in (1, 4):

                return candidate.strftime(
                    "%Y-%m-%d"
                )

        return (
            today + timedelta(days=3)
        ).strftime("%Y-%m-%d")

