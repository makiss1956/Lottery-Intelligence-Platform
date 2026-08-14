"""Prediction vs Reality Dashboard."""
from typing import Dict, Any
from src.database.db_manager import DBManager
from src.core.logger import get_logger

logger = get_logger("Dashboard")

class SuccessDashboard:
    def __init__(self, db_manager: DBManager = None):
        self.db = db_manager or DBManager()

    def generate_report(self) -> Dict[str, Any]:
        history = self.db.get_all_draws()

        if not history:
            return {"message": "No evaluated predictions yet."}

        total = len(history)

        return {
            "total_evaluated": total,
            "recent_predictions": history[:10]
        }

    def print_cli_report(self):
        r = self.generate_report()
        print("\n" + "=" * 60)
        print("📊 PREDICTION SUCCESS DASHBOARD")
        print("=" * 60)
        print(f"Total Evaluated Draws: {r.get('total_evaluated', 0)}")
        print("=" * 60 + "\n")

    def generate_html_report(self, output_path: str = "reports/dashboard.html"):
        import os
        r = self.generate_report()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Lottery Intelligence Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 Lottery Intelligence Dashboard</h1>
        <p>Total Draws in Database: {r.get('total_evaluated', 0)}</p>
    </div>
</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("HTML dashboard saved to %s", output_path)
        return output_path
