import json
import urllib.request
from typing import List, Dict, Any, Optional
from datetime import datetime

class EurojackpotImporter:
    """
    Importer for Eurojackpot draw results and historical data.
    """
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.api_url = "https://api.opap.gr/draws/v3.0/5104/last-result/1"

    def fetch_latest_draw(self) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest draw result from the OPAP API for Eurojackpot.
        """
        try:
            req = urllib.request.Request(
                self.api_url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    draw = data[0] if isinstance(data, list) else data
                    
                    # Extract numbers and euro numbers
                    winning_numbers = draw.get('winningNumbers', {})
                    list_numbers = winning_numbers.get('list', [])
                    bonus_numbers = winning_numbers.get('bonus', [])
                    
                    # Convert draw time (milliseconds to ISO format)
                    draw_time_ms = draw.get('drawTime')
                    draw_date = datetime.utcfromtimestamp(draw_time_ms / 1000.0).strftime('%Y-%m-%d') if draw_time_ms else datetime.utcnow().strftime('%Y-%m-%d')

                    raw_payload = {
                        "date": draw_date,
                        "numbers": list_numbers,
                        "euro_numbers": bonus_numbers
                    }
                    return self.parse_draw_data(raw_payload)
        except Exception as e:
    print(f"Error fetching draw data: {e}")
    return None

    def parse_draw_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses raw draw JSON data into a standardized format.
        """
        draw_date = raw_data.get("date")
        numbers = raw_data.get("numbers", [])
        euro_numbers = raw_data.get("euro_numbers", [])

        if not draw_date or not numbers:
            raise ValueError("Invalid draw data format.")

        return {
            "lottery_name": "Eurojackpot",
            "draw_date": draw_date,
            "numbers": sorted(numbers),
            "euro_numbers": sorted(euro_numbers),
            "created_at": datetime.utcnow().isoformat()
        }

    def save_draw(self, draw_data: Dict[str, Any]) -> bool:
        """
        Saves a parsed draw to the database via DatabaseManager.
        """
        if not self.db_manager:
            print("Warning: DatabaseManager not configured.")
            return False

        parsed = self.parse_draw_data(draw_data) if "lottery_name" not in draw_data else draw_data
        return self.db_manager.insert_draw(parsed)
