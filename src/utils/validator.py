from typing import List, Dict, Any
from datetime import datetime

class DrawValidator:
    """
    Validates draw data structure, numbers range, and date formats.
    """

    @staticmethod
    def validate_eurojackpot_draw(draw_data: Dict[str, Any]) -> bool:
        """
        Validates a EuroJackpot draw dictionary.
        - Must contain 5 main numbers between 1 and 50.
        - Must contain 2 euro numbers between 1 and 12.
        - Draw date must be a valid ISO format date string.
        """
        numbers = draw_data.get("numbers", [])
        euro_numbers = draw_data.get("euro_numbers", [])
        draw_date = draw_data.get("draw_date")

        if not draw_date:
            return False

        try:
            datetime.fromisoformat(draw_date)
        except ValueError:
            return False

        if len(numbers) != 5 or len(set(numbers)) != 5:
            return False

        if not all(1 <= num <= 50 for num in numbers):
            return False

        if len(euro_numbers) != 2 or len(set(euro_numbers)) != 2:
            return False

        if not all(1 <= num <= 12 for num in euro_numbers):
            return False

        return True
