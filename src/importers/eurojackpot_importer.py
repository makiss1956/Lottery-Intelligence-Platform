"""Eurojackpot Data Importer using OPAP Official API."""
import requests
from datetime import datetime, timedelta
from src.core.logger import get_logger

logger = get_logger("EurojackpotImporter")

class EurojackpotImporter:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        # Επίσημο API ΟΠΑΠ για το Eurojackpot (Game ID 5104)
        self.api_url_last = "https://api.opap.gr/draws/v3.0/5104/last-result/12"
        self.api_url_history = "https://api.opap.gr/draws/v3.0/5104/last/50"

    def fetch_latest_draw(self):
        """Fetch the single latest draw from OPAP API."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(self.api_url_last, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            draws = data if isinstance(data, list) else [data]
            if not draws:
                return None

            latest = draws[0]
            draw_time = latest.get("drawTime")
            if isinstance(draw_time, (int, float)):
                draw_date = datetime.fromtimestamp(draw_time / 1000).strftime("%Y-%m-%d")
            else:
                draw_date = str(draw_time)[:10]

            winning_numbers = latest.get("winningNumbers", {})
            primary = winning_numbers.get("list", [])
            euro = winning_numbers.get("bonus", [])

            return {
                "draw_id": latest.get("drawId"),
                "draw_date": draw_date,
                "primary_numbers": primary,
                "euro_numbers": euro
            }
        except Exception as e:
            logger.error("Failed to fetch latest draw from OPAP API: %s", e)
            return None

    def sync_history(self):
        """Fetch recent history (last 50 draws) and update the database."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(self.api_url_history, headers=headers, timeout=10)
            if response.status_code == 200:
                draws = response.json()
                count = 0
                for d in draws:
                    draw_time = d.get("drawTime")
                    if isinstance(draw_time, (int, float)):
                        draw_date = datetime.fromtimestamp(draw_time / 1000).strftime("%Y-%m-%d")
                    else:
                        draw_date = str(draw_time)[:10]

                    w_nums = d.get("winningNumbers", {})
                    draw_obj = {
                        "draw_id": d.get("drawId"),
                        "draw_date": draw_date,
                        "primary_numbers": w_nums.get("list", []),
                        "euro_numbers": w_nums.get("bonus", [])
                    }
                    if self.db_manager:
                        inserted = self.db_manager.insert_draw(draw_obj)
                        if inserted:
                            count += 1
                logger.info("Successfully synced draw history. New draws added: %d", count)
        except Exception as e:
            logger.warning("History sync encountered an issue: %s", e)

    def get_next_draw_date(self):
        """Calculate next Eurojackpot draw date (Tuesday or Friday)."""
        today = datetime.now()
        weekday = today.weekday()  # Monday=0, Tuesday=1, Friday=4
        hour = today.hour

        if weekday == 1 and hour < 21:
            target = today
        elif weekday == 4 and hour < 21:
            target = today
        else:
            days_ahead = 1
            while True:
                next_day = today + timedelta(days=days_ahead)
                if next_day.weekday() in (1, 4):
                    target = next_day
                    break
                days_ahead += 1

        return target.strftime("%Y-%m-%d")
