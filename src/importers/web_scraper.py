"""Eurojackpot Web Scraper — fetches latest draw from official source."""
import re
import requests
from datetime import datetime
from typing import Optional, Dict, List
from src.core.logger import get_logger

logger = get_logger("WebScraper")

class EurojackpotWebScraper:
    """Scrapes latest Eurojackpot results from multiple sources."""
    
    # Πηγές με JSON API (πιο αξιόπιστες)
    SOURCES = [
        "https://www.lottoland.com/api/drawings/eurojackpot/latest",
        "https://www.euro-jackpot.org/en/results",
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
        })
    
    def fetch_latest_draw(self) -> Optional[Dict]:
        """Try multiple sources to get latest draw."""
        for source in self.SOURCES:
            try:
                result = self._fetch_from_source(source)
                if result:
                    return result
            except Exception as e:
                logger.warning("Source %s failed: %s", source, e)
                continue
        return None
    
    def _fetch_from_source(self, url: str) -> Optional[Dict]:
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        
        # Try JSON first
        try:
            data = resp.json()
            return self._parse_json(data)
        except ValueError:
            pass
        
        # Fallback to HTML parsing
        return self._parse_html(resp.text)
    
    def _parse_json(self, data: dict) -> Optional[Dict]:
        """Parse JSON response from lottery API."""
        try:
            draw = data.get("lastDraw", {}) or data.get("latest", {})
            if not draw:
                return None
            
            date_str = draw.get("date", draw.get("drawDate", ""))
            numbers = draw.get("numbers", [])
            euro_numbers = draw.get("euroNumbers", draw.get("additionalNumbers", []))
            
            if len(numbers) == 5 and len(euro_numbers) == 2:
                return {
                    "draw_date": self._normalize_date(date_str),
                    "primary_numbers": sorted([int(n) for n in numbers]),
                    "euro_numbers": sorted([int(n) for n in euro_numbers]),
                }
        except Exception as e:
            logger.error("JSON parse error: %s", e)
        return None
    
    def _parse_html(self, html: str) -> Optional[Dict]:
        """Parse HTML for numbers using regex."""
        # Look for number patterns like: 5, 12, 23, 34, 45 + 2, 8
        pattern = r'(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})'
        matches = re.findall(pattern, html)
        if matches:
            nums = [int(x) for x in matches[0]]
            if all(1 <= n <= 50 for n in nums):
                # Try to find euro numbers
                euro_pattern = r'[\+|E]\s*(\d{1,2})\s*,\s*(\d{1,2})'
                euro_matches = re.findall(euro_pattern, html)
                if euro_matches:
                    euro = [int(x) for x in euro_matches[0]]
                    if all(1 <= n <= 12 for n in euro):
                        return {
                            "draw_date": datetime.now().strftime("%Y-%m-%d"),
                            "primary_numbers": sorted(nums),
                            "euro_numbers": sorted(euro),
                        }
        return None
    
    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """Convert various date formats to YYYY-MM-DD."""
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y-%m-%d")
