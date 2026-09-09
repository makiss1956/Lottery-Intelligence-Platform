"""
Database Manager for Lottery Intelligence Platform.
Handles:
- Eurojackpot draw storage
- Prediction storage
- Prediction validation
- SQLite initialization
- Duplicate prevention
"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.core.logger import get_logger

logger = get_logger("DBManager")


class DBManager:
    """SQLite database manager for Eurojackpot data."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            db_dir = base_dir / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "lottery.db")
        else:
            self.db_path = db_path

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a configured SQLite connection."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Create required database tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS eurojackpot_draws (
                    draw_date TEXT PRIMARY KEY,
                    primary_numbers TEXT NOT NULL,
                    euro_numbers TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_date TEXT NOT NULL,
                    for_draw_date TEXT NOT NULL,
                    predicted_primary TEXT NOT NULL,
                    predicted_euro TEXT NOT NULL,
                    method TEXT,
                    confidence TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_predictions_for_draw_date
                ON predictions(for_draw_date)
                """
            )
            conn.commit()
        logger.info("Database initialized: %s", self.db_path)

    def initialize_database(self) -> None:
        """Compatibility alias."""
        self._init_db()

    @staticmethod
    def _parse_num_string(num_str: str) -> List[int]:
        """Convert '1,2,3' into [1, 2, 3]."""
        if not num_str:
            return []
        return [
            int(value.strip())
            for value in num_str.split(",")
            if value.strip()
        ]

    def insert_draw(self, draw: Dict[str, Any]) -> bool:
        primary = draw.get("primary_numbers", [])
        euro = draw.get("euro_numbers", [])
        draw_date = draw.get("draw_date")

        if not draw_date:
            logger.error("Draw has no date.")
            return False

        if len(primary) != 5 or len(euro) != 2:
            logger.error(
                "Invalid draw structure: primary=%s euro=%s",
                len(primary),
                len(euro),
            )
            return False

        if len(set(primary)) != 5 or len(set(euro)) != 2:
            logger.error("Duplicate numbers in draw.")
            return False

        if not all(1 <= n <= 50 for n in primary) or not all(1 <= n <= 12 for n in euro):
            logger.error("Numbers out of bounds.")
            return False

        primary_str = ",".join(map(str, sorted(primary)))
        euro_str = ",".join(map(str, sorted(euro)))

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO eurojackpot_draws
                    (draw_date, primary_numbers, euro_numbers)
                    VALUES (?, ?, ?)
                    """,
                    (draw_date, primary_str, euro_str),
                )
                conn.commit()
                inserted = cursor.rowcount > 0
                if inserted:
                    logger.info("NEW DRAW INSERTED: %s | %s | %s", draw_date, primary_str, euro_str)
                else:
                    logger.info("Draw already exists: %s", draw_date)
                return inserted
        except sqlite3.Error as exc:
            logger.error("Failed to insert draw %s: %s", draw_date, exc)
            return False

    def _fetch_draws_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [
                {
                    "draw_date": row["draw_date"],
                    "primary_numbers": self._parse_num_string(row["primary_numbers"]),
                    "euro_numbers": self._parse_num_string(row["euro_numbers"]),
                }
                for row in rows
            ]

    def get_all_draws(self) -> List[Dict[str, Any]]:
        return self._fetch_draws_query(
            "SELECT draw_date, primary_numbers, euro_numbers FROM eurojackpot_draws ORDER BY draw_date DESC"
        )

    def get_latest_draws(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._fetch_draws_query(
            "SELECT draw_date, primary_numbers, euro_numbers FROM eurojackpot_draws ORDER BY draw_date DESC LIMIT ?",
            (limit,),
        )

    def get_draw_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM eurojackpot_draws")
            return int(cursor.fetchone()[0])

    def get_draw(self, draw_date: str) -> Optional[Dict[str, Any]]:
        results = self._fetch_draws_query(
            "SELECT draw_date, primary_numbers, euro_numbers FROM eurojackpot_draws WHERE draw_date = ?",
            (draw_date,),
        )
        return results[0] if results else None

    def execute(self, sql: str, parameters: tuple = ()) -> None:
        with self._get_connection() as conn:
            conn.execute(sql, parameters)
            conn.commit()

    def prediction_exists(self, for_draw_date: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM predictions WHERE for_draw_date = ? LIMIT 1", (for_draw_date,))
            return cursor.fetchone() is not None

    def insert_prediction(self, prediction: Dict[str, Any]) -> bool:
        prediction_date = prediction.get("prediction_date")
        for_draw_date = prediction.get("for_draw_date")
        predicted_primary = prediction.get("predicted_primary", [])
        predicted_euro = prediction.get("predicted_euro", [])
        method_name = prediction.get("method") or prediction.get("model_name", "")

        if not prediction_date or not for_draw_date:
            logger.error("Prediction date or target draw date missing.")
            return False

        if not (
            (len(predicted_primary) == 7 and len(predicted_euro) == 3) or
            (len(predicted_primary) == 5 and len(predicted_euro) == 2)
        ):
            logger.error("Invalid prediction layout: %s+%s", len(predicted_primary), len(predicted_euro))
            return False

        confidence_value = prediction.get("confidence", {})
        confidence_string = (
            json.dumps(confidence_value, ensure_ascii=False)
            if isinstance(confidence_value, (dict, list))
            else str(confidence_value)
        )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO predictions
                    (prediction_date, for_draw_date, predicted_primary, predicted_euro, method, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prediction_date,
                        for_draw_date,
                        ",".join(map(str, sorted(predicted_primary))),
                        ",".join(map(str, sorted(predicted_euro))),
                        method_name,
                        confidence_string,
                    ),
                )
                conn.commit()
                inserted = cursor.rowcount > 0
                if inserted:
                    logger.info("NEW PREDICTION SAVED for %s", for_draw_date)
                else:
                    logger.warning("Prediction already exists for %s.", for_draw_date)
                return inserted
        except sqlite3.Error as exc:
            logger.error("Failed to insert prediction: %s", exc)
            return False

    def get_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions ORDER BY prediction_date DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                raw_conf = row["confidence"]
                try:
                    conf = json.loads(raw_conf) if raw_conf else {}
                except (json.JSONDecodeError, TypeError):
                    conf = raw_conf
                result.append(
                    {
                        "id": row["id"],
                        "prediction_date": row["prediction_date"],
                        "for_draw_date": row["for_draw_date"],
                        "predicted_primary": self._parse_num_string(row["predicted_primary"]),
                        "predicted_euro": self._parse_num_string(row["predicted_euro"]),
                        "model_name": row["method"],
                        "method": row["method"],
                        "confidence": conf,
                    }
                )
            return result

    def get_prediction_for_draw(self, draw_date: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions WHERE for_draw_date = ? ORDER BY prediction_date DESC LIMIT 1", (draw_date,))
            row = cursor.fetchone()
            if row is None:
                return None
            raw_conf = row["confidence"]
            try:
                conf = json.loads(raw_conf) if raw_conf else {}
            except (json.JSONDecodeError, TypeError):
                conf = raw_conf
            return {
                "id": row["id"],
                "prediction_date": row["prediction_date"],
                "for_draw_date": row["for_draw_date"],
                "predicted_primary": self._parse_num_string(row["predicted_primary"]),
                "predicted_euro": self._parse_num_string(row["predicted_euro"]),
                "model_name": row["method"],
                "method": row["method"],
                "confidence": conf,
            }

    def validate_prediction_for_draw(self, actual_draw: Dict[str, Any]) -> Dict[str, Any]:
        draw_date = actual_draw.get("draw_date")
        if not draw_date:
            logger.error("Cannot validate draw without date.")
            return {}

        prediction = self.get_prediction_for_draw(draw_date)
        if prediction is None:
            logger.info("No prediction found for draw %s.", draw_date)
            return {}

        actual_primary = actual_draw.get("primary_numbers", [])
        actual_euro = actual_draw.get("euro_numbers", [])

        if not actual_primary and not actual_euro:
            logger.warning("Actual draw contains no numbers for date %s.", draw_date)
            return {
                "prediction_id": prediction["id"],
                "prediction_date": prediction["prediction_date"],
                "predicted_primary": prediction["predicted_primary"],
                "predicted_euro": prediction["predicted_euro"],
                "main_hits_count": 0,
                "euro_hits_count": 0,
                "target_achieved": False,
                "error": "Empty draw numbers",
            }

        from src.analytics.backtester import Backtester

        result = Backtester.evaluate_prediction(
            predicted_mains=prediction["predicted_primary"],
            predicted_euros=prediction["predicted_euro"],
            actual_draw=actual_draw,
        )
        result.update({
            "prediction_id": prediction["id"],
            "prediction_date": prediction["prediction_date"],
            "predicted_primary": prediction["predicted_primary"],
            "predicted_euro": prediction["predicted_euro"],
        })

        logger.info("VALIDATION COMPLETE | Draw=%s | Main Hits=%s | Euro Hits=%s", draw_date, result.get("main_hits_count"), result.get("euro_hits_count"))
        return result
