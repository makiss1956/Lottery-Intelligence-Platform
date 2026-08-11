"""Unified Database Manager for Eurojackpot data and predictions."""
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_path: Optional[str] = "data/lottery_data.db"):
        if db_path is None:
        db_path = "data/lottery_data.db"
        self.db_path = db_path
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        schema_path = Path(__file__).resolve().parent / "schema.sql"
        if not schema_path.exists():
            logger.error("Schema file not found: %s", schema_path)
            return
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()
        try:
            with self.get_connection() as conn:
                conn.executescript(schema)
                conn.commit()
            logger.info("Database schema initialized.")
        except Exception as e:
            logger.error("Failed to initialize DB: %s", e)
            raise

    # ---------- Draw Operations ----------

    def insert_draw(self, draw: Dict[str, Any]) -> bool:
        """Insert a draw. Returns True if inserted, False if duplicate."""
        query = """
            INSERT OR IGNORE INTO eurojackpot_draws 
            (draw_number, draw_date, n1, n2, n3, n4, n5, e1, e2, jackpot_euros)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, (
                    draw.get("draw_number"),
                    draw.get("draw_date"),
                    draw["primary_numbers"][0], draw["primary_numbers"][1],
                    draw["primary_numbers"][2], draw["primary_numbers"][3],
                    draw["primary_numbers"][4],
                    draw["euro_numbers"][0], draw["euro_numbers"][1],
                    draw.get("jackpot_euros")
                ))
                conn.commit()
                inserted = cur.rowcount > 0
                if inserted:
                    logger.info("Inserted draw %s (%s)", draw.get("draw_number"), draw.get("draw_date"))
                else:
                    logger.info("Draw %s already exists.", draw.get("draw_number"))
                return inserted
        except Exception as e:
            logger.error("Insert draw error: %s", e)
            return False

    def draw_exists(self, draw_date: str) -> bool:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM eurojackpot_draws WHERE draw_date = ?", (draw_date,)
            ).fetchone()
            return row is not None

    def get_latest_draw(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM eurojackpot_draws ORDER BY draw_date DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            return self._row_to_draw(row)

    def get_all_draws(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM eurojackpot_draws ORDER BY draw_date ASC"
            ).fetchall()
            return [self._row_to_draw(r) for r in rows]

    def get_draw_count(self) -> int:
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM eurojackpot_draws").fetchone()
            return row[0] if row else 0

    def _row_to_draw(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "draw_number": row["draw_number"],
            "draw_date": row["draw_date"],
            "primary_numbers": [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"]],
            "euro_numbers": [row["e1"], row["e2"]],
            "jackpot_euros": row["jackpot_euros"],
            "created_at": row["created_at"]
        }

    # ---------- Prediction Operations ----------

    def save_prediction(self, prediction: Dict[str, Any]) -> int:
        """Save a prediction. Returns the prediction id."""
        query = """
            INSERT INTO predictions 
            (prediction_for_date, predicted_primary, predicted_euro, method)
            VALUES (?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cur = conn.execute(query, (
                prediction["prediction_for_date"],
                ",".join(map(str, prediction["predicted_primary"])),
                ",".join(map(str, prediction["predicted_euro"])),
                prediction.get("method", "frequency_7_3")
            ))
            conn.commit()
            pred_id = cur.lastrowid
            logger.info("Saved prediction id=%s for %s", pred_id, prediction["prediction_for_date"])
            return pred_id

    def get_unevaluated_prediction(self) -> Optional[Dict[str, Any]]:
        """Get the most recent prediction that has not been evaluated yet."""
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM predictions 
                   WHERE evaluated_at IS NULL 
                   ORDER BY created_at DESC LIMIT 1"""
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def evaluate_prediction(self, pred_id: int, actual_draw: Dict[str, Any]) -> None:
        """Evaluate a prediction against an actual draw."""
        pred_row = conn = self.get_connection()
        with conn:
            pred = conn.execute(
                "SELECT * FROM predictions WHERE id = ?", (pred_id,)
            ).fetchone()
            if not pred:
                logger.warning("Prediction %s not found for evaluation.", pred_id)
                return

            pred_primary = [int(x) for x in pred["predicted_primary"].split(",") if x.strip()]
            pred_euro = [int(x) for x in pred["predicted_euro"].split(",") if x.strip()]

            actual_primary = set(actual_draw["primary_numbers"])
            actual_euro = set(actual_draw["euro_numbers"])

            matched_main = sorted(list(set(pred_primary).intersection(actual_primary)))
            matched_euro = sorted(list(set(pred_euro).intersection(actual_euro)))

            main_hits = len(matched_main)
            euro_hits = len(matched_euro)
            score_pct = round((main_hits / 5.0) * 100, 2)

            conn.execute("""
                UPDATE predictions SET
                    actual_draw_number = ?,
                    actual_primary = ?,
                    actual_euro = ?,
                    main_hits = ?,
                    euro_hits = ?,
                    matched_main = ?,
                    matched_euro = ?,
                    score_percentage = ?,
                    evaluated_at = datetime('now')
                WHERE id = ?
            """, (
                actual_draw["draw_number"],
                ",".join(map(str, actual_draw["primary_numbers"])),
                ",".join(map(str, actual_draw["euro_numbers"])),
                main_hits, euro_hits,
                ",".join(map(str, matched_main)) if matched_main else None,
                ",".join(map(str, matched_euro)) if matched_euro else None,
                score_pct,
                pred_id
            ))
            conn.commit()
            logger.info(
                "Evaluated prediction %s: %s/5 main hits, %s/2 euro hits, score=%s%%",
                pred_id, main_hits, euro_hits, score_pct
            )

    def get_prediction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM predictions 
                   ORDER BY created_at DESC LIMIT ?""", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
