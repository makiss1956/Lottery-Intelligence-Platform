"""
SQLite database manager for the Lottery Intelligence Platform.

Stores:
- Eurojackpot historical draws
- Generated predictions

The class is intentionally small and stable because several parts
of the project depend on it.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DBManager:
    """Manage the SQLite database used by the lottery pipeline."""

    def __init__(self, db_path: str = "data/lottery.db") -> None:
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None

        if db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row

        else:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.initialize_database()

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Return a database connection."""
        if self._shared_conn is not None:
            return self._shared_conn

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _close_connection(self, connection: sqlite3.Connection) -> None:
        """Close a non-shared connection."""
        if connection is not self._shared_conn:
            connection.close()

    # ------------------------------------------------------------------
    # Database initialization
    # ------------------------------------------------------------------

    def initialize_database(self) -> None:
        """Create the required database tables if they do not exist."""
        connection = self._get_connection()

        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS draws (
                    draw_date TEXT PRIMARY KEY,
                    primary_numbers TEXT NOT NULL,
                    euro_numbers TEXT NOT NULL
                )
                """
            )

            connection.execute(
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

            # Safety migration: ensure model_name column exists if table was created previously without it
            cursor = connection.execute("PRAGMA table_info(predictions)")
            columns = [col["name"] for col in cursor.fetchall()]
            if "model_name" not in columns:
                connection.execute("ALTER TABLE predictions ADD COLUMN model_name TEXT NOT NULL DEFAULT 'Hybrid Ensemble'")

            connection.commit()

        finally:
            self._close_connection(connection)

    # ------------------------------------------------------------------
    # Draw operations
    # ------------------------------------------------------------------

    def insert_draw(self, draw: Dict[str, Any]) -> bool:
        """
        Insert a draw.

        Returns:
            True  -> draw was inserted.
            False -> draw already existed.
        """
        draw_date = draw["draw_date"]
        primary_numbers = draw["primary_numbers"]
        euro_numbers = draw["euro_numbers"]

        connection = self._get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO draws (
                    draw_date,
                    primary_numbers,
                    euro_numbers
                )
                VALUES (?, ?, ?)
                """,
                (
                    draw_date,
                    json.dumps(list(primary_numbers)),
                    json.dumps(list(euro_numbers)),
                ),
            )

            connection.commit()
            return cursor.rowcount > 0

        except sqlite3.IntegrityError:
            connection.rollback()
            return False

        finally:
            self._close_connection(connection)

    def replace_draw(self, draw: Dict[str, Any]) -> bool:
        """
        Replace an existing draw with corrected data.

        Returns:
            True if the draw was successfully stored.
        """
        draw_date = draw["draw_date"]
        primary_numbers = draw["primary_numbers"]
        euro_numbers = draw["euro_numbers"]

        connection = self._get_connection()

        try:
            connection.execute(
                "DELETE FROM draws WHERE draw_date = ?",
                (draw_date,),
            )

            connection.execute(
                """
                INSERT INTO draws (
                    draw_date,
                    primary_numbers,
                    euro_numbers
                )
                VALUES (?, ?, ?)
                """,
                (
                    draw_date,
                    json.dumps(list(primary_numbers)),
                    json.dumps(list(euro_numbers)),
                ),
            )

            connection.commit()
            return True

        except Exception:
            connection.rollback()
            raise

        finally:
            self._close_connection(connection)

    def get_draw(self, draw_date: str) -> Optional[Dict[str, Any]]:
        """Return one draw by date."""
        connection = self._get_connection()

        try:
            row = connection.execute(
                """
                SELECT
                    draw_date,
                    primary_numbers,
                    euro_numbers
                FROM draws
                WHERE draw_date = ?
                """,
                (draw_date,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_draw(row)

        finally:
            self._close_connection(connection)

    def get_latest_draw(self) -> Optional[Dict[str, Any]]:
        """Return the most recent draw."""
        connection = self._get_connection()

        try:
            row = connection.execute(
                """
                SELECT
                    draw_date,
                    primary_numbers,
                    euro_numbers
                FROM draws
                ORDER BY draw_date DESC
                LIMIT 1
                """
            ).fetchone()

            if row is None:
                return None

            return self._row_to_draw(row)

        finally:
            self._close_connection(connection)

    def get_all_draws(self) -> List[Dict[str, Any]]:
        """Return all draws ordered from oldest to newest."""
        connection = self._get_connection()

        try:
            rows = connection.execute(
                """
                SELECT
                    draw_date,
                    primary_numbers,
                    euro_numbers
                FROM draws
                ORDER BY draw_date ASC
                """
            ).fetchall()

            return [self._row_to_draw(row) for row in rows]

        finally:
            self._close_connection(connection)

    def get_draw_count(self) -> int:
        """Return the number of stored draws."""
        connection = self._get_connection()

        try:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM draws"
            ).fetchone()

            return int(row["count"])

        finally:
            self._close_connection(connection)

    # ------------------------------------------------------------------
    # Prediction operations
    # ------------------------------------------------------------------

    def insert_prediction(self, prediction: Dict[str, Any]) -> bool:
        """
        Insert a prediction.

        The target draw date is UNIQUE, so the same prediction target
        cannot accidentally be stored twice.
        """
        prediction_date = prediction.get(
            "prediction_date",
            datetime.utcnow().strftime("%Y-%m-%d"),
        )

        for_draw_date = prediction["for_draw_date"]

        model_name = prediction.get(
            "model_name",
            prediction.get(
                "method",
                "Hybrid Ensemble",
            ),
        )

        predicted_primary = prediction["predicted_primary"]
        predicted_euro = prediction["predicted_euro"]

        connection = self._get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO predictions (
                    prediction_date,
                    for_draw_date,
                    model_name,
                    predicted_primary,
                    predicted_euro
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    prediction_date,
                    for_draw_date,
                    model_name,
                    json.dumps(list(predicted_primary)),
                    json.dumps(list(predicted_euro)),
                ),
            )

            connection.commit()
            return cursor.rowcount > 0

        except sqlite3.IntegrityError:
            connection.rollback()
            return False

        finally:
            self._close_connection(connection)

    def save_prediction(
        self,
        for_draw_date: str,
        primary_numbers: List[int],
        euro_numbers: List[int],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save a prediction using the public project API.

        Metadata is currently used for the model name. The prediction
        numbers remain stored in the dedicated database columns.
        """
        metadata = metadata or {}

        model_name = metadata.get(
            "model_name",
            metadata.get(
                "method",
                "Hybrid Ensemble",
            ),
        )

        prediction = {
            "prediction_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "for_draw_date": for_draw_date,
            "model_name": model_name,
            "predicted_primary": list(primary_numbers),
            "predicted_euro": list(euro_numbers),
        }

        return self.insert_prediction(prediction)

    def get_predictions(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return predictions, newest first."""
        connection = self._get_connection()

        try:
            sql = """
                SELECT
                    id,
                    prediction_date,
                    for_draw_date,
                    model_name,
                    predicted_primary,
                    predicted_euro
                FROM predictions
                ORDER BY prediction_date DESC, id DESC
            """

            parameters: tuple[Any, ...] = ()

            if limit is not None:
                if limit <= 0:
                    return []

                sql += " LIMIT ?"
                parameters = (limit,)

            rows = connection.execute(
                sql,
                parameters,
            ).fetchall()

            return [self._row_to_prediction(row) for row in rows]

        finally:
            self._close_connection(connection)

    def prediction_exists(self, draw_date: str) -> bool:
        """Return True if a prediction already exists for a draw date."""
        connection = self._get_connection()

        try:
            row = connection.execute(
                """
                SELECT 1
                FROM predictions
                WHERE for_draw_date = ?
                LIMIT 1
                """,
                (draw_date,),
            ).fetchone()

            return row is not None

        finally:
            self._close_connection(connection)

    # ------------------------------------------------------------------
    # Internal conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_numbers(value: Any) -> List[int]:
        """Convert stored JSON numbers into a list of integers."""
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return []
        else:
            decoded = value

        if not isinstance(decoded, list):
            return []

        return [int(number) for number in decoded]

    @classmethod
    def _row_to_draw(cls, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a SQLite draw row into a normal dictionary."""
        return {
            "draw_date": row["draw_date"],
            "primary_numbers": cls._decode_numbers(
                row["primary_numbers"]
            ),
            "euro_numbers": cls._decode_numbers(
                row["euro_numbers"]
            ),
        }

    @classmethod
    def _row_to_prediction(
        cls,
        row: sqlite3.Row,
    ) -> Dict[str, Any]:
        """Convert a SQLite prediction row into a normal dictionary."""
        return {
            "id": row["id"],
            "prediction_date": row["prediction_date"],
            "for_draw_date": row["for_draw_date"],
            "model_name": row["model_name"],
            "predicted_primary": cls._decode_numbers(
                row["predicted_primary"]
            ),
            "predicted_euro": cls._decode_numbers(
                row["predicted_euro"]
            ),
        }
