"""
Eurojackpot Data Importer.

CSV is the primary source.
The importer synchronizes all valid CSV rows
into the SQLite database using idempotent inserts.
"""

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Path setup για standalone execution
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

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
    def _normalize_csv_date(date_str: str) -> Optional[str]:
        """
        ✅ ΠΡΟΣΘΗΚΗ: Μετατρέπει διάφορα formats σε YYYY-MM-DD.
        """
        date_str = date_str.strip()
        if not date_str or date_str.lower() in ("date", "yyyy-mm-dd"):
            return None

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_row(
        row: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Convert one CSV row to normalized draw data."""

        date_str = row.get(
            "Date",
            "",
        ).strip()

        normalized_date = EurojackpotImporter._normalize_csv_date(date_str)
        if not normalized_date:
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
            "draw_date": normalized_date,  # ✅ ΔΙΟΡΘΩΣΗ: πάντα YYYY-MM-DD
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
        ✅ ΔΙΟΡΘΩΣΗ: Υπολογίζει σωστά την επόμενη κλήρωση Eurojackpot.
        Οι κληρώσεις είναι Τρίτη και Παρασκευή στις 21:00 CET (22:00 EEST).
        Αν τρέχει μετά την κλήρωση, πάει στην επόμενη.
        """
        # Χρησιμοποιούμε UTC και μετατρέπουμε σε CET (UTC+1) / CEST (UTC+2)
        now = datetime.utcnow()
        # Προσέγγιση: CET = UTC+1, CEST = UTC+2. Χρησιμοποιούμε UTC+2 για καλοκαίρι.
        # Για ακρίβεια, θα μπορούσαμε να χρησιμοποιήσουμε pytz, αλλά για απλότητα:
        cet_hour = (now.hour + 2) % 24  # Προσέγγιση CEST
        cet_weekday = (now.weekday() + (1 if now.hour >= 22 else 0)) % 7  # Προσέγγιση

        # Η κλήρωση γίνεται στις 21:00 CET. Αν η ώρα CET είναι > 21:00,
        # η "σήμερα" θεωρείται ότι έχει περάσει.
        draw_hour = 21

        today = now.date()
        weekday = today.weekday()

        # Tuesday (1) or Friday (4)
        if weekday == 1:  # Tuesday
            if cet_hour < draw_hour:
                return today.strftime("%Y-%m-%d")
            else:
                # Μετά την κλήρωση Τρίτης -> επόμενη Παρασκευή
                return (today + timedelta(days=3)).strftime("%Y-%m-%d")

        if weekday == 4:  # Friday
            if cet_hour < draw_hour:
                return today.strftime("%Y-%m-%d")
            else:
                # Μετά την κλήρωση Παρασκευής -> επόμενη Τρίτη
                return (today + timedelta(days=4)).strftime("%Y-%m-%d")

        # Άλλες μέρες: βρες την επόμενη Τρίτη ή Παρασκευή
        for days_ahead in range(1, 8):
            candidate = today + timedelta(days=days_ahead)
            if candidate.weekday() in (1, 4):
                return candidate.strftime("%Y-%m-%d")

        # Defensive fallback
        return (today + timedelta(days=3)).strftime("%Y-%m-%d")
