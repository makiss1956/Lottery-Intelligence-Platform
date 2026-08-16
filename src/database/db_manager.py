"""Database Manager for SQLite storage."""
import json
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
        # Προσθήκη timeout για αποφυγή database locks
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Ενεργοποίηση WAL mode για καλύτερη απόδοση σε παράλληλες λειτουργίες
        conn.execute("PRAGMA journal_mode=WAL;")
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

    @staticmethod
    def _parse_num_string(num_str: str) -> List[int]:
        """Βοηθητική μέθοδος: Μετατρέπει το string "1,2,3" σε λίστα [1, 2, 3]."""
        if not num_str:
            return []
        return [int(x) for x in num_str.split(",") if x.strip()]

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

    def _fetch_draws_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Βοηθητική μέθοδος για την εκτέλεση ερωτημάτων αναζήτησης κληρώσεων."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [
                {
                    "draw_date": r["draw_date"],
                    "primary_numbers": self._parse_num_string(r["primary_numbers"]),
                    "euro_numbers": self._parse_num_string(r["euro_numbers"])
                }
                for r in rows
            ]

    def get_all_draws(self) -> List[Dict[str, Any]]:
        return self._fetch_draws_query(
            "SELECT draw_date, primary_numbers, euro_numbers FROM eurojackpot_draws ORDER BY draw_date DESC"
        )

    def get_latest_draws(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._fetch_draws_query(
            "SELECT draw_date, primary_numbers, euro_numbers FROM eurojackpot_draws ORDER BY draw_date DESC LIMIT ?",
            (limit,)
        )

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
            # Διόρθωση: Αποθήκευση του confidence ως έγκυρο JSON string
            confidence_val = prediction.get("confidence", {})
            if isinstance(confidence_val, (dict, list)):
                confidence_str = json.dumps(confidence_val)
            else:
                confidence_str = str(confidence_val)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO predictions 
                    (prediction_date, for_draw_date, predicted_primary, predicted_euro, method, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prediction.get("prediction_date"),
                    prediction.get("for_draw_date"),
                    ",".join(map(str, sorted(prediction.get("predicted_primary", [])))),
                    ",".join(map(str, sorted(prediction.get("predicted_euro", [])))),
                    prediction.get("method", ""),
                    confidence_str
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
                raw_conf = r["confidence"]
                # Διόρθωση: Ανάγνωση του JSON string επιστρέφοντας πάλι dictionary/object
                try:
                    conf_data = json.loads(raw_conf) if raw_conf else {}
                except (json.JSONDecodeError, TypeError):
                    conf_data = raw_conf

                result.append({
                    "id": r["id"],
                    "prediction_date": r["prediction_date"],
                    "for_draw_date": r["for_draw_date"],
                    "predicted_primary": self._parse_num_string(r["predicted_primary"]),
                    "predicted_euro": self._parse_num_string(r["predicted_euro"]),
                    "method": r["method"],
                    "confidence": conf_data
                })
            return result

    def validate_latest_prediction(self, latest_draw: dict) -> dict:
        """Ελέγχει αν η τελευταία πρόβλεψη ταίριαξε με την πραγματική κλήρωση."""
        predictions = self.get_predictions(limit=1)
        if not predictions:
            logger.info("No previous prediction to validate.")
            return {}

        last_pred = predictions[0]
        if last_pred["for_draw_date"] != latest_draw.get("draw_date"):
            logger.info("Latest prediction was for %s, but latest draw is %s. Skipping validation.",
                        last_pred["for_draw_date"], latest_draw.get("draw_date"))
            return {}

        from src.analytics.backtester import Backtester
        result = Backtester.evaluate_prediction(
            predicted_mains=last_pred["predicted_primary"],
            predicted_euros=last_pred["predicted_euro"],
            actual_draw=latest_draw
        )

        logger.info(
            "Validation for %s: Main Hits = %d/5, Euro Hits = %d/2, Success = %s",
            latest_draw.get("draw_date"),
            result["main_hits_count"],
            result["euro_hits_count"],
            "YES" if result["target_achieved"] else "NO"
        )
        return result
