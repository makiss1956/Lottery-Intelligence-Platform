"""Eurojackpot Data Importer with OPAP API + Web Scraping fallback."""
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.core.logger import get_logger

logger = get_logger("EurojackpotImporter")

class EurojackpotImporter:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        # OPAP API (Game ID 5104 = Eurojackpot)
        self.api_url_last = "https://api.opap.gr/draws/v3.0/5104/last-result/12"
        self.api_url_history = "https://api.opap.gr/draws/v3.0/5104/last/50"

    def fetch_latest_draw(self):
        """Try OPAP API first, fallback to web scraping."""
        draw = self._fetch_from_api()
        if draw:
            logger.info("Fetched latest draw from OPAP API: %s", draw.get("draw_date"))
            return draw

        draw = self._fetch_from_web()
        if draw:
            logger.info("Fetched latest draw from web fallback: %s", draw.get("draw_date"))
            return draw

        logger.error("Could not fetch latest draw from any source.")
        return None

    def _fetch_from_api(self):
        """Fetch from OPAP API."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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

            if len(primary) != 5 or len(euro) != 2:
                return None

            return {
                "draw_id": latest.get("drawId"),
                "draw_date": draw_date,
                "primary_numbers": sorted(primary),
                "euro_numbers": sorted(euro)
            }
        except Exception as e:
            logger.warning("OPAP API failed: %s", e)
            return None

    def _fetch_from_web(self):
        """Fallback: scrape from euro-jackpot.org."""
        try:
            url = "https://www.euro-jackpot.org/en/results/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try to find date
            date_elem = soup.find("time") or soup.find("span", class_=re.compile("date", re.I))
            draw_date = None
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                draw_date = self._parse_date(date_text)
            if not draw_date:
                draw_date = self._guess_last_draw_date()

            # Find all ball numbers
            nums = []
            for b in soup.find_all("span", class_=re.compile("ball", re.I)):
                txt = b.get_text(strip=True)
                if txt.isdigit():
                    nums.append(int(txt))

            if len(nums) < 7:
                logger.warning("Web scrape found only %d numbers, expected 7+", len(nums))
                return None

            primary = sorted(nums[:5])
            euro = sorted(nums[5:7])

            return {
                "draw_id": None,
                "draw_date": draw_date,
                "primary_numbers": primary,
                "euro_numbers": euro
            }
        except Exception as e:
            logger.warning("Web fallback failed: %s", e)
            return None

    def sync_history(self):
        """Fetch recent history and update database."""
        if not self.db_manager:
            return

        # Only sync if database is empty
        if self.db_manager.get_draw_count() > 5:
            logger.info("Database already has draws, skipping history sync.")
            return

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
                    inserted = self.db_manager.insert_draw(draw_obj)
                    if inserted:
                        count += 1
                logger.info("History sync complete. New draws added: %d", count)
        except Exception as e:
            logger.warning("History sync failed: %s", e)

    def get_next_draw_date(self):
        """Calculate next Eurojackpot draw date (Tuesday or Friday)."""
        today = datetime.now()
        weekday = today.weekday()
        hour = today.hour

        # Eurojackpot draw is at ~19:00 UTC (22:00 Greece summer)
        # If today is draw day and it's before 20:00 UTC, next draw is today
        if weekday == 1 and hour < 20:
            target = today
        elif weekday == 4 and hour < 20:
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

    def _guess_last_draw_date(self):
        """Guess the most recent completed draw date."""
        today = datetime.now()
        weekday = today.weekday()
        hour = today.hour

        if weekday == 1 and hour >= 20:
            return today.strftime("%Y-%m-%d")
        elif weekday == 4 and hour >= 20:
            return today.strftime("%Y-%m-%d")
        elif weekday > 4:
            days_back = weekday - 4
            return (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        elif weekday > 1:
            days_back = weekday - 1
            return (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        elif weekday == 0:
            return (today - timedelta(days=3)).strftime("%Y-%m-%d")
        else:
            return (today - timedelta(days=4)).strftime("%Y-%m-%d")

    def _parse_date(self, text: str):
        """Try common date formats."""
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
