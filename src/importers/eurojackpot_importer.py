"""Eurojackpot Data Importer with API + Web + CSV fallback."""
import csv
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.logger import get_logger

logger = get_logger("EurojackpotImporter")

class EurojackpotImporter:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        # Correct OPAP API endpoints for Eurojackpot (gameId=5104)
        self.api_url_last = "https://api.opap.gr/draws/v3.0/5104/last-result"
        self.api_url_history = "https://api.opap.gr/draws/v3.0/5104/last/50"
        # CSV fallback path
        self.csv_path = Path("data/eurojackpot_raw_history.csv")

    def fetch_latest_draw(self):
        """Try API first, then web, then CSV."""
        draw = self._fetch_from_api()
        if draw:
            logger.info("Fetched from OPAP API: %s", draw.get("draw_date"))
            return draw

        draw = self._fetch_from_web()
        if draw:
            logger.info("Fetched from web: %s", draw.get("draw_date"))
            return draw

        draw = self._fetch_from_csv()
        if draw:
            logger.info("Fetched from CSV: %s", draw.get("draw_date"))
            return draw

        logger.error("All fetch methods failed.")
        return None

    def _fetch_from_api(self):
        """Fetch from OPAP API (no /12 suffix)."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json"
            }
            resp = requests.get(self.api_url_last, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # The API returns the draw directly, not a list
            if isinstance(data, list):
                latest = data[0]
            else:
                latest = data

            draw_time = latest.get("drawTime")
            if isinstance(draw_time, (int, float)):
                draw_date = datetime.fromtimestamp(draw_time / 1000).strftime("%Y-%m-%d")
            else:
                draw_date = str(draw_time)[:10]

            wn = latest.get("winningNumbers", {})
            primary = wn.get("list", [])
            euro = wn.get("bonus", [])

            if len(primary) != 5 or len(euro) != 2:
                logger.warning("API returned invalid numbers: primary=%s, euro=%s", len(primary), len(euro))
                return None

            return {
                "draw_date": draw_date,
                "primary_numbers": sorted([int(x) for x in primary]),
                "euro_numbers": sorted([int(x) for x in euro])
            }
        except Exception as e:
            logger.warning("API failed: %s", e)
            return None

    def _fetch_from_web(self):
        """Scrape from euro-jackpot.org (follow redirects, use http)."""
        try:
            url = "http://www.euro-jackpot.org/en/results/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find date
            date_elem = soup.find("time") or soup.find("span", class_=re.compile("date", re.I))
            draw_date = None
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                draw_date = self._parse_date(date_text)
            if not draw_date:
                draw_date = self._guess_last_draw_date()

            # Find balls
            nums = []
            for b in soup.find_all("span", class_=re.compile("ball", re.I)):
                txt = b.get_text(strip=True)
                if txt.isdigit():
                    nums.append(int(txt))

            if len(nums) < 7:
                logger.warning("Web scrape found only %d numbers", len(nums))
                return None

            primary = sorted(nums[:5])
            euro = sorted(nums[5:7])

            return {
                "draw_date": draw_date,
                "primary_numbers": primary,
                "euro_numbers": euro
            }
        except Exception as e:
            logger.warning("Web scrape failed: %s", e)
            return None

    def _fetch_from_csv(self):
        """Read last row from local CSV."""
        if not self.csv_path.exists():
            logger.warning("CSV not found: %s", self.csv_path)
            return None
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = list(reader)
            if not rows:
                return None
            last = rows[-1]
            return {
                "draw_date": last.get("Date", "").strip(),
                "primary_numbers": sorted([
                    int(last.get(f"N{i}", 0)) for i in range(1, 6) if last.get(f"N{i}")
                ]),
                "euro_numbers": sorted([
                    int(last.get(f"E{i}", 0)) for i in range(1, 3) if last.get(f"E{i}")
                ])
            }
        except Exception as e:
            logger.warning("CSV read failed: %s", e)
            return None

    def sync_history(self):
        """Sync last 50 draws from API to database (only if DB has < 5 draws)."""
        if not self.db_manager:
            return
        if self.db_manager.get_draw_count() >= 5:
            logger.info("DB already has %d draws, skipping history sync.", self.db_manager.get_draw_count())
            return

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(self.api_url_history, headers=headers, timeout=15)
            resp.raise_for_status()
            draws = resp.json()

            count = 0
            for d in draws:
                draw_time = d.get("drawTime")
                if isinstance(draw_time, (int, float)):
                    draw_date = datetime.fromtimestamp(draw_time / 1000).strftime("%Y-%m-%d")
                else:
                    draw_date = str(draw_time)[:10]

                wn = d.get("winningNumbers", {})
                draw_obj = {
                    "draw_date": draw_date,
                    "primary_numbers": wn.get("list", []),
                    "euro_numbers": wn.get("bonus", [])
                }
                if self.db_manager.insert_draw(draw_obj):
                    count += 1
            logger.info("History sync: %d new draws added.", count)
        except Exception as e:
            logger.warning("History sync failed: %s", e)

    def get_next_draw_date(self):
