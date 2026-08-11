"""Eurojackpot data importer with web scraping + CSV fallback."""

import os
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

 from src.database.db_manager import DBManager
 from src.core.config import get_config
 from src.core.logger import get_logger
"""Eurojackpot data importer with web scraping + CSV fallback."""

import os
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

from src.database.db_manager import DBManager
    """Fetches latest Eurojackpot draw data."""

    def __init__(self):
        self.cfg = get_config()
        temp_csv_path = self.cfg.get("importer.csv_path")
        if temp_csv_path is None:
            temp_csv_path = "data/eurojackpot_raw_history.csv"
        self.csv_path = Path(temp_csv_path)
       
        self.delimiter = self.cfg.get("importer.csv_delimiter", ";")
        self.fallback_to_csv = self.cfg.get("importer.fallback_to_csv", True)

    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """Try web first, fallback to CSV. Returns latest draw dict or None."""
        draw = self._fetch_from_web()
        if draw:
            logger.info("Fetched latest draw from web: %s", draw.get("draw_date"))
            return draw
        if self.fallback_to_csv:
            draw = self._fetch_from_csv()
            if draw:
                logger.info("Fetched latest draw from CSV fallback: %s", draw.get("draw_date"))
                return draw
        logger.warning("Could not fetch latest draw from any source.")
        return None

    def _fetch_from_web(self) -> Optional[Dict[str, Any]]:
        """Scrape latest results from euro-jackpot.org."""
        try:
            url = "https://www.euro-jackpot.org/en/results/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try to find the latest result box
            # The site structure: latest results in a container with balls
            # This is a best-effort parser — may need adjustment if site changes
            result_box = soup.find("div", class_=re.compile("result", re.I))
            if not result_box:
                # Alternative: look for ball elements
                balls = soup.find_all("span", class_=re.compile("ball", re.I))
                if len(balls) < 7:
                    return None
                nums = [int(b.get_text(strip=True)) for b in balls if b.get_text(strip=True).isdigit()]
                if len(nums) >= 7:
                    primary = sorted(nums[:5])
                    euro = sorted(nums[5:7])
                    # Guess date as last draw day (Fri or Tue)
                    draw_date = self._guess_last_draw_date()
                    return {
                        "draw_number": None,  # Will be inferred
                        "draw_date": draw_date,
                        "primary_numbers": primary,
                        "euro_numbers": euro,
                        "jackpot_euros": None
                    }

            # If we found a result box, parse it
            date_elem = soup.find("time") or soup.find("span", class_=re.compile("date", re.I))
            draw_date = None
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                draw_date = self._parse_date(date_text)
            if not draw_date:
                draw_date = self._guess_last_draw_date()

            nums = []
            for b in soup.find_all("span", class_=re.compile("ball", re.I)):
                txt = b.get_text(strip=True)
                if txt.isdigit():
                    nums.append(int(txt))
            if len(nums) < 7:
                return None

            primary = sorted(nums[:5])
            euro = sorted(nums[5:7])

            return {
                "draw_number": None,
                "draw_date": draw_date,
                "primary_numbers": primary,
                "euro_numbers": euro,
                "jackpot_euros": None
            }
        except Exception as e:
            logger.warning("Web fetch failed: %s", e)
            return None

    def _fetch_from_csv(self) -> Optional[Dict[str, Any]]:
        """Read the last row from the local CSV file."""
        if not self.csv_path.exists():
            logger.warning("CSV file not found: %s", self.csv_path)
            return None
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                rows = list(reader)
            if not rows:
                return None
            last = rows[-1]
            # CSV columns: Date;N1;N2;N3;N4;N5;E1;E2;Jackpot_Euros
            return {
                "draw_number": None,
                "draw_date": last.get("Date", "").strip(),
                "primary_numbers": sorted([
                    int(last.get(f"N{i}", 0)) for i in range(1, 6)
                ]),
                "euro_numbers": sorted([
                    int(last.get(f"E{i}", 0)) for i in range(1, 3)
                ]),
                "jackpot_euros": float(last.get("Jackpot_Euros", 0) or 0)
            }
        except Exception as e:
            logger.error("CSV read error: %s", e)
            return None

    def _guess_last_draw_date(self) -> str:
        """Guess the most recent draw date (Tue or Fri)."""
        today = datetime.now()
        # Eurojackpot draws: Tuesday (1) and Friday (4)
        weekday = today.weekday()
        if weekday == 1:  # Tuesday
            return today.strftime("%Y-%m-%d")
        elif weekday == 4:  # Friday
            return today.strftime("%Y-%m-%d")
        elif weekday > 4:  # Sat/Sun -> last Friday
            days_back = weekday - 4
            return (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        elif weekday > 1:  # Wed/Thu -> last Tuesday
            days_back = weekday - 1
            return (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        else:  # Monday -> last Friday
            return (today - timedelta(days=3)).strftime("%Y-%m-%d")

    def _parse_date(self, text: str) -> Optional[str]:
        """Try common date formats."""
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def fetch_latest_draws(self) -> List[Dict[str, Any]]:
        """Compatibility wrapper returning list."""
        draw = self.fetch_latest_draw()
        return [draw] if draw else []
