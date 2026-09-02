"""Eurojackpot Web Scraper — fetches latest draw from official source."""
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Path setup για standalone execution
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

import requests
from src.core.logger import get_logger

logger = get_logger("WebScraper")

class EurojackpotWebScraper:
    """Scrapes latest Eurojackpot results from multiple sources."""
    
    # ✅ ΔΙΟΡΘΩΣΗ: Πιο αξιόπιστες πηγές με καλύτερα endpoints
    SOURCES = [
        "https://www.euro-jackpot.org/en/results",
        "https://www.lotteryextreme.com/eurojackpot/results",
    ]
    
    def __init__(self):
        self.session = requests.Session()
        # ✅ ΔΙΟΡΘΩΣΗ: Σωστό User-Agent
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
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
        logger.error("All web sources failed. No draw data available.")
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
        return self._parse_html(resp.text, url)
    
    def _parse_json(self, data: dict) -> Optional[Dict]:
        """Parse JSON response from lottery API."""
        try:
            draw = data.get("lastDraw", {}) or data.get("latest", {}) or data.get("draw", {})
            if not draw:
                return None
            
            date_str = draw.get("date", draw.get("drawDate", draw.get("draw_date", "")))
            numbers = draw.get("numbers", draw.get("mainNumbers", []))
            euro_numbers = draw.get("euroNumbers", draw.get("additionalNumbers", draw.get("extraNumbers", [])))
            
            if len(numbers) == 5 and len(euro_numbers) == 2:
                return {
                    "draw_date": self._normalize_date(date_str),
                    "primary_numbers": sorted([int(n) for n in numbers]),
                    "euro_numbers": sorted([int(n) for n in euro_numbers]),
                }
        except Exception as e:
            logger.error("JSON parse error: %s", e)
        return None
    
    def _parse_html(self, html: str, url: str) -> Optional[Dict]:
        """
        ✅ ΔΙΟΡΘΩΣΗ: Robust HTML parsing με πολλαπλά patterns.
        """
        # Pattern 1: Αναζήτηση για σαφή number blocks (euro-jackpot.org style)
        # Π.χ. <span class="ball">5</span> ... <span class="euro">2</span>
        primary_patterns = [
            r'<span[^>]*class=["\']?ball["\']?[^>]*>\s*(\d{1,2})\s*</span>',
            r'<div[^>]*class=["\']?ball["\']?[^>]*>\s*(\d{1,2})\s*</div>',
            r'class=["\']?num["\']?[^>]*>\s*(\d{1,2})\s*<',
        ]
        
        euro_patterns = [
            r'<span[^>]*class=["\']?euro["\']?[^>]*>\s*(\d{1,2})\s*</span>',
            r'<span[^>]*class=["\']?extra["\']?[^>]*>\s*(\d{1,2})\s*</span>',
            r'[\+]\s*(\d{1,2})',  # + 2, + 8
            r'E\s*(\d{1,2})',     # E 2, E 8
        ]
        
        # Προσπάθησε να βρεις primary numbers
        primary = []
        for pattern in primary_patterns:
            matches = re.findall(pattern, html)
            if len(matches) >= 5:
                primary = [int(x) for x in matches[:5]]
                break
        
        if not primary or not all(1 <= n <= 50 for n in primary):
            # Pattern 2: Generic 5-number sequence
            seq_pattern = r'(\d{1,2})\s*[,;]\s*(\d{1,2})\s*[,;]\s*(\d{1,2})\s*[,;]\s*(\d{1,2})\s*[,;]\s*(\d{1,2})'
            matches = re.findall(seq_pattern, html)
            for match in matches:
                nums = [int(x) for x in match]
                if all(1 <= n <= 50 for n in nums) and len(set(nums)) == 5:
                    primary = sorted(nums)
                    break
        
        if not primary:
            return None
        
        # Προσπάθησε να βρεις euro numbers
        euro = []
        for pattern in euro_patterns:
            matches = re.findall(pattern, html)
            if len(matches) >= 2:
                euro = [int(x) for x in matches[:2]]
                break
        
        if not euro or not all(1 <= n <= 12 for n in euro) or len(set(euro)) != 2:
            return None
        
        return {
            "draw_date": datetime.now().strftime("%Y-%m-%d"),
            "primary_numbers": sorted(primary),
            "euro_numbers": sorted(euro),
        }
    
    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """Convert various date formats to YYYY-MM-DD."""
        date_str = date_str.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y-%m-%d")
