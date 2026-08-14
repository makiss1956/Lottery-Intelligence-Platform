"""Prediction vs Reality Dashboard."""
import os
from typing import Dict, Any
from src.database.db_manager import DBManager
from src.analytics.backtester import Backtester
from src.core.logger import get_logger

logger = get_logger("Dashboard")

class SuccessDashboard:
    def __init__(self, db_manager: DBManager = None):
        self.db = db_manager or DBManager()

    def generate_report(self) -> Dict[str, Any]:
        predictions = self.db.get_predictions(limit=100)
        draws = {d["draw_date"]: d for d in self.db.get_all_draws()}
        
        evaluated = []
        for pred in predictions:
            actual = draws.get(pred["for_draw_date"])
            if actual:
                result = Backtester.evaluate_prediction(
                    predicted_mains=pred["predicted_primary"],
                    predicted_euros=pred["predicted_euro"],
                    actual_draw=actual
                )
                evaluated.append({
                    "for_draw_date": pred["for_draw_date"],
                    "predicted_primary": pred["predicted_primary"],
                    "predicted_euro": pred["predicted_euro"],
                    "actual_primary": actual["primary_numbers"],
                    "actual_euro": actual["euro_numbers"],
                    "main_hits": result["main_hits_count"],
                    "euro_hits": result["euro_hits_count"],
                    "matched_main": result["matched_main_numbers"],
                    "matched_euro": result["matched_euro_numbers"],
                    "success": result["target_achieved"]
                })
        
        return {"evaluated": evaluated, "total": len(evaluated)}

    def generate_html_report(self, output_path: str = "reports/dashboard.html"):
        import os
        r = self.generate_report()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Calculate statistics
        total = r["total"]
        successful = sum(1 for e in r["evaluated"] if e["success"])
        avg_main_hits = round(sum(e["main_hits"] for e in r["evaluated"]) / total, 2) if total else 0
        
        rows = ""
        for e in r["evaluated"]:
            rows += f"""
            <tr>
                <td>{e['for_draw_date']}</td>
                <td>{', '.join(map(str, e['predicted_primary']))}</td>
                <td>{', '.join(map(str, e['actual_primary']))}</td>
                <td>{e['main_hits']}/5</td>
                <td>{', '.join(map(str, e['matched_main'])) if e['matched_main'] else '-'}</td>
                <td>{', '.join(map(str, e['predicted_euro']))}</td>
                <td>{', '.join(map(str, e['actual_euro']))}</td>
                <td>{e['euro_hits']}/2</td>
                <td style="color:{'green' if e['success'] else 'red'}; font-weight:bold;">{'✅ YES' if e['success'] else '❌ NO'}</td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Lottery Intelligence Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f0f2f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a237e; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #e8eaf6; padding: 15px 25px; border-radius: 8px; text-align: center; }}
        .stat-box h3 {{ margin: 0; color: #3949ab; font-size: 28px; }}
        .stat-box p {{ margin: 5px 0 0; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
        th {{ background: #3949ab; color: white; font-weight: 600; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        tr:hover {{ background: #e3f2fd; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 Eurojackpot — Predictions vs Reality</h1>
        <div class="stats">
            <div class="stat-box">
                <h3>{total}</h3>
                <p>Total Evaluated</p>
            </div>
            <div class="stat-box">
                <h3>{successful}</h3>
                <p>Successful (≥3 hits)</p>
            </div>
            <div class="stat-box">
                <h3>{round((successful/total)*100, 1) if total else 0}%</h3>
                <p>Success Rate</p>
            </div>
            <div class="stat-box">
                <h3>{avg_main_hits}</h3>
                <p>Avg Main Hits</p>
            </div>
        </div>
        <table>
            <tr>
                <th>Draw Date</th>
                <th>Predicted Primary</th>
                <th>Actual Primary</th>
                <th>Main Hits</th>
                <th>Matched Numbers</th>
                <th>Predicted Euro</th>
                <th>Actual Euro</th>
                <th>Euro Hits</th>
                <th>Success (≥3)</th>
            </tr>
            {rows}
        </table>
        <div class="footer">
            Lottery Intelligence Platform — Educational & Research Purposes Only
        </div>
    </div>
</body>
</html>"""
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("HTML dashboard saved to %s", output_path)
        return output_path
