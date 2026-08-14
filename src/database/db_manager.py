"""Database Manager for SQLite storage."""
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.core.logger import get_logger

logger = get_logger("DBManager")

class DBManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            db_dir = base_dir / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "lottery.db")
        else:
            self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eurojackpot_draws (
                    draw_date TEXT PRIMARY KEY,
                    primary_numbers TEXT NOT NULL,
                    euro_numbers TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_date TEXT NOT NULL,
                    for_draw_date TEXT NOT NULL,
                    predicted_primary TEXT NOT NULL,
                    predicted_euro TEXT NOT NULL,
                    method TEXT,
                    confidence TEXT
                )
            """)
            conn.commit()

    def initialize_database(self):
        """Alias for test compatibility."""
        self._init_db()

    def insert_draw(self, draw: dict) -> bool:
        p = draw.get("primary_numbers", [])
        e = draw.get("euro_numbers", [])
        if len(p) != 5 or len(e) != 2:
            logger.error("Invalid draw structure: primary=%s, euro=%s", len(p), len(e))
            return False
        if not all(1 <= n <= 50 for n in p) or not all(1 <= n <= 12 for n in e):
            logger.error("Number out of range in draw.")
            return False

        primary_str = ",".join(map(str, sorted(p)))
        euro_str = ",".join(map(str, sorted(e)))
        draw_date = draw.get("draw_date")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO eurojackpot_draws (draw_date, primary_numbers, euro_numbers)
                    VALUES (?, ?, ?)
                """, (draw_date, primary_str, euro_str))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as err:
            logger.error("Failed to insert draw %s: %s", draw_date, err)
            return False

    def get_all_draws(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT draw_date, primary_numbers, euro_numbers FROM eurojackpot_draws ORDER BY draw_date DESC")
            rows = cursor.fetchall()
            
            result = []
            for r in rows:
                result.append({
                    "draw_date": r["draw_date"],
                    "primary_numbers": [int(x) for x in r["primary_numbers"].split(",") if x],
                    "euro_numbers": [int(x) for x in r["euro_numbers"].split(",") if x]
                })
            return result

    def get_latest_draws(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT draw_date, primary_numbers, euro_numbers 
                FROM eurojackpot_draws 
                ORDER BY draw_date DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    "draw_date": r["draw_date"],
                    "primary_numbers": [int(x) for x in r["primary_numbers"].split(",") if x],
                    "euro_numbers": [int(x) for x in r["euro_numbers"].split(",") if x]
                })
            return result

    def get_draw_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM eurojackpot_draws")
            return cursor.fetchone()[0]

    def execute(self, sql: str, parameters: tuple = ()):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters)
            conn.commit()

    def insert_prediction(self, prediction: dict) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO predictions 
                    (prediction_date, for_draw_date, predicted_primary, predicted_euro, method, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prediction.get("prediction_date"),
                    prediction.get("for_draw_date"),
                    ",".join(map(str, prediction.get("predicted_primary", []))),
                    ",".join(map(str, prediction.get("predicted_euro", []))),
                    prediction.get("method", ""),
                    str(prediction.get("confidence", {}))
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to insert prediction: %s", e)
            return False

    def get_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM predictions 
                ORDER BY prediction_date DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "prediction_date": r["prediction_date"],
                    "for_draw_date": r["for_draw_date"],
                    "predicted_primary": [int(x) for x in r["predicted_primary"].split(",") if x],
                    "predicted_euro": [int(x) for x in r["predicted_euro"].split(",") if x],
                    "method": r["method"],
                    "confidence": r["confidence"]
                })
            return result
