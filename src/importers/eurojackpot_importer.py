"""Eurojackpot Data Importer — CSV-based with optional API fallback."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
from src.core.logger import get_logger

logger = get_logger("EurojackpotImporter")

class EurojackpotImporter:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.csv_path = Path("data/eurojackpot_raw_history.csv")

    def fetch_latest_draw(self):
        """Read the latest draw from CSV."""
        return self._fetch_from_csv()

    def _fetch_from_csv(self):
        """Read last row from local CSV."""
        if not self.csv_path.exists():
            logger.error("CSV not found: %s", self.csv_path)
            return None
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = list(reader)
            if not rows:
                logger.warning("CSV is empty")
                return None
            
            last = rows[-1]
            date_str = last.get("Date", "").strip()
            primary = []
            euro = []
            
            for i in range(1, 6):
                val = last.get(f"N{i}", "").strip()
                if val.isdigit():
                    n = int(val)
                    if 1 <= n <= 50:
                        primary.append(n)
            
            for i in range(1, 3):
                val = last.get(f"E{i}", "").strip()
                if val.isdigit():
                    n = int(val)
                    if 1 <= n <= 12:
                        euro.append(n)
            
            if len(primary) != 5 or len(euro) != 2:
                logger.error("CSV has invalid numbers: primary=%s, euro=%s", primary, euro)
                return None
            
            return {
                "draw_date": date_str,
                "primary_numbers": sorted(primary),
                "euro_numbers": sorted(euro),
            }
        except Exception as e:
            logger.error("CSV read failed: %s", e)
            return None

    def sync_history(self):
        """Sync all CSV rows to database (only if DB has < 5 draws)."""
        if not self.db_manager:
            return
        if self.db_manager.get_draw_count() >= 5:
            logger.info("DB already has %d draws, skipping sync.", self.db_manager.get_draw_count())
            return

        if not self.csv_path.exists():
            logger.error("CSV not found for sync: %s", self.csv_path)
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = list(reader)
            
            count = 0
            for row in rows:
                date_str = row.get("Date", "").strip()
                primary = []
                euro = []
                
                for i in range(1, 6):
                    val = row.get(f"N{i}", "").strip()
                    if val.isdigit():
                        n = int(val)
                        if 1 <= n <= 50:
                            primary.append(n)
                
                for i in range(1, 3):
                    val = row.get(f"E{i}", "").strip()
                    if val.isdigit():
                        n = int(val)
                        if 1 <= n <= 12:
                            euro.append(n)
                
                if len(primary) == 5 and len(euro) == 2:
                    draw_obj = {
                        "draw_date": date_str,
                        "primary_numbers": sorted(primary),
                        "euro_numbers": sorted(euro),
                    }
                    if self.db_manager.insert_draw(draw_obj):
                        count += 1
            
            logger.info("CSV sync complete: %d new draws added.", count)
        except Exception as e:
            logger.error("CSV sync failed: %s", e)

    def get_next_draw_date(self):
        """Next Eurojackpot draw: Tuesday or Friday."""
        today = datetime.now()
        weekday = today.weekday()
        hour = today.hour

        if weekday == 1 and hour < 22:
            return today.strftime("%Y-%m-%d")
        elif weekday == 4 and hour < 22:
            return today.strftime("%Y-%m-%d")

        days_ahead = 1
        while True:
            next_day = today + timedelta(days=days_ahead)
            if next_day.weekday() in (1, 4):
                return next_day.strftime("%Y-%m-%d")
            days_ahead += 1
