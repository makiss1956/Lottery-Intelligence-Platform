import json
import urllib.request
from typing import List, Dict, Any, Optional
from datetime import datetime

class EuroJackpotImporter:
    """
    Importer for EuroJackpot draw results and historical data.
    """

    def __init__(self, db_manager=None):
        self.db_manager = db_manager

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
            "lottery_name": "EuroJackpot",
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

        parsed = self.parse_draw_data(draw_data)
        # Assuming database_manager has a method to insert draws
        return self.db_manager.insert_draw(parsed)

