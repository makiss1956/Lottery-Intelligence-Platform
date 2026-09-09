"""
Database Manager Module for handling SQLite operations.
"""

import json
import logging
import sqlite3
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class DBManager:

    def __init__(self, db_path="data/lottery.db"):
        self.db_path = db_path
        self.initialize_database()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Δημιουργία των απαραίτητων πινάκων στη βάση δεδομένων."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Πίνακας αποτελεσμάτων κληρώσεων
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS draws (
                    draw_date TEXT PRIMARY KEY,
                    primary_numbers TEXT NOT NULL,
                    euro_numbers TEXT NOT NULL
                )
            """
            )

            # Πίνακας προβλέψεων μοντέλων
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_date TEXT NOT NULL,
                    for_draw_date TEXT UNIQUE NOT NULL,
                    model_name TEXT NOT NULL,
                    predicted_primary TEXT NOT NULL,
                    predicted_euro TEXT NOT NULL
                )
            """
            )
            conn.commit()

    def insert_draw(self, draw: dict) -> bool:
        """Εισαγωγή αποτελέσματος κλήρωσης."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO draws (draw_date, primary_numbers, euro_numbers) VALUES (?, ?, ?)",
                    (
                        draw["draw_date"],
                        json.dumps(draw["primary_numbers"]),
                        json.dumps(draw["euro_numbers"]),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error inserting draw: {e}")
            return False

    def get_all_draws(self) -> List[Dict[str, Any]]:
        """Επιστρέφει όλες τις καταχωρημένες κληρώσεις αποσυσκευασμένες από JSON."""
        draws = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT draw_date, primary_numbers, euro_numbers FROM draws ORDER BY draw_date ASC")
                rows = cursor.fetchall()
                for row in rows:
                    draws.append({
                        "draw_date": row["draw_date"],
                        "primary_numbers": json.loads(row["primary_numbers"]),
                        "euro_numbers": json.loads(row["euro_numbers"]),
                    })
        except Exception as e:
            logger.error(f"Error fetching draws: {e}")
        return draws

    def insert_prediction(self, prediction: dict) -> bool:
        """Εισαγωγή πρόβλεψης μοντέλου."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO predictions 
                    (prediction_date, for_draw_date, model_name, predicted_primary, predicted_euro)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        prediction["prediction_date"],
                        prediction["for_draw_date"],
                        prediction["model_name"],
                        json.dumps(prediction["predicted_primary"]),
                        json.dumps(prediction["predicted_euro"]),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error inserting prediction: {e}")
            return False

    def prediction_exists(self, draw_date: str) -> bool:
        """Έλεγχος αν υπάρχει πρόβλεψη για συγκεκριμένη κλήρωση."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM predictions WHERE for_draw_date = ?",
                (draw_date,),
            )
            return cursor.fetchone() is not None

    def get_draw_count(self) -> int:
        """Επιστρέφει το πλήθος των καταχωρημένων κληρώσεων."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM draws")
            return cursor.fetchone()[0]
