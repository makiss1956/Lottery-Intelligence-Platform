"""
Database Manager for Lottery Intelligence Platform.
Handles SQLite connection, schema, draws, predictions, and evaluation.
"""

import sqlite3
import os
from pathlib import Path
import logging

logger = logging.getLogger("lottery_pipeline")

class DBManager:
    def __init__(self, db_path="data/lottery.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        schema_path = Path("src/database/schema.sql")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    cursor.executescript(f.read())
            else:
                # Fallback minimal schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS eurojackpot_draws (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        draw_number TEXT,
                        draw_date TEXT UNIQUE NOT NULL,
                        n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER,
                        e1 INTEGER, e2 INTEGER,
                        jackpot_euros REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prediction_for_date TEXT NOT NULL,
                        predicted_primary TEXT NOT NULL,
                        predicted_euro TEXT NOT NULL,
                        method TEXT DEFAULT 'frequency_7_3',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        evaluated_at TIMESTAMP,
                        actual_draw_number TEXT,
                        actual_primary TEXT,
                        actual_euro TEXT,
                        main_hits INTEGER,
                        euro_hits INTEGER,
                        matched_main TEXT,
                        matched_euro TEXT,
                        score_percentage REAL
                    );
                """)
            conn.commit()
        logger.info("Database initialized.")

    # ---------- Draw Operations ----------

    def insert_draw(self, draw: dict) -> bool:
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
                    logger.info("Inserted draw %s", draw.get("draw_date"))
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

    def get_latest_draw(self):
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM eurojackpot_draws ORDER BY draw_date DESC LIMIT 1"
            ).fetchone()
            return self._row_to_draw(row) if row else None

    def get_all_draws(self):
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM eurojackpot_draws ORDER BY draw_date ASC"
            ).fetchall()
            return [self._row_to_draw(r) for r in rows]

    def _row_to_draw(self, row):
        """Convert DB row to standard draw dict with primary_numbers/euro_numbers lists."""
        return {
            "draw_number": row["draw_number"],
            "draw_date": row["draw_date"],
            "primary_numbers": [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"]],
            "euro_numbers": [row["e1"], row["e2"]],
            "jackpot_euros": row["jackpot_euros"],
            "created_at": row["created_at"]
        }

    # ---------- Prediction Operations ----------

    def save_prediction(self, prediction: dict) -> int:
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

    def get_unevaluated_prediction(self):
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM predictions
                WHERE evaluated_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            """).fetchone()
            return dict(row) if row else None

    def evaluate_prediction(self, pred_id: int, actual_draw: dict) -> None:
        with self.get_connection() as conn:
            pred = conn.execute(
                "SELECT * FROM predictions WHERE id = ?", (pred_id,)
            ).fetchone()
            if not pred:
                logger.warning("Prediction %s not found.", pred_id)
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
                actual_draw.get("draw_number"),
                ",".join(map(str, actual_draw["primary_numbers"])),
                ",".join(map(str, actual_draw["euro_numbers"])),
                main_hits, euro_hits,
                ",".join(map(str, matched_main)) if matched_main else None,
                ",".join(map(str, matched_euro)) if matched_euro else None,
                score_pct,
                pred_id
            ))
            conn.commit()
            logger.info("Evaluated prediction %s: %s/5 main, %s/2 euro, score=%s%%",
                        pred_id, main_hits, euro_hits, score_pct)

    def get_prediction_history(self, limit: int = 50):
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_evaluated_predictions(self, limit: int = 50):
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM predictions
                WHERE evaluated_at IS NOT NULL
                ORDER BY prediction_for_date DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ---------- Generic Queries ----------

    def execute_query(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetch_all(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def fetch_one(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()


# Alias for compatibility
DatabaseManager = DBManager
