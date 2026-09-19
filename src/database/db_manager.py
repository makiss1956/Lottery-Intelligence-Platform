```python
"""
Database manager for Lottery Intelligence Platform.

Stores:
- Eurojackpot draws
- Predictions
- Prediction history

Prediction format:
- 3 main numbers
- 1 Joker/Euro number
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger

logger = get_logger("DBManager")


class DBManager:

    def __init__(self, db_path: Optional[str] = None) -> None:

        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            self.db_path = str(data_dir / "lottery.db")

        else:
            self.db_path = db_path

        self.initialize_database()

    # ---------------------------------------------------------
    # Connection
    # ---------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ---------------------------------------------------------
    # Database initialization
    # ---------------------------------------------------------

    def initialize_database(self) -> None:

        with self._get_connection() as connection:

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

            connection.commit()

        logger.info(
            "Database initialized: %s",
            self.db_path,
        )

    # ---------------------------------------------------------
    # Draws
    # ---------------------------------------------------------

    def insert_draw(
        self,
        draw: Dict[str, Any],
    ) -> bool:

        draw_date = draw["draw_date"]
        primary = sorted(draw["primary_numbers"])
        euro = sorted(draw["euro_numbers"])

        if len(primary) != 5:
            raise ValueError("A draw must contain 5 main numbers.")

        if len(euro) != 2:
            raise ValueError("A draw must contain 2 Euro numbers.")

        with self._get_connection() as connection:

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO draws
                (
                    draw_date,
                    primary_numbers,
                    euro_numbers
                )
                VALUES (?, ?, ?)
                """,
                (
                    draw_date,
                    json.dumps(primary),
                    json.dumps(euro),
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

    def replace_draw(
        self,
        draw: Dict[str, Any],
    ) -> bool:

        with self._get_connection() as connection:

            connection.execute(
                "DELETE FROM draws WHERE draw_date = ?",
                (draw["draw_date"],),
            )

            connection.execute(
                """
                INSERT INTO draws
                (
                    draw_date,
                    primary_numbers,
                    euro_numbers
                )
                VALUES (?, ?, ?)
                """,
                (
                    draw["draw_date"],
                    json.dumps(sorted(draw["primary_numbers"])),
                    json.dumps(sorted(draw["euro_numbers"])),
                ),
            )

            connection.commit()

        return True

    def get_draw(
        self,
        draw_date: str,
    ) -> Optional[Dict[str, Any]]:

        with self._get_connection() as connection:

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

    def get_latest_draw(self) -> Optional[Dict[str, Any]]:

        with self._get_connection() as connection:

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

    def get_all_draws(self) -> List[Dict[str, Any]]:

        with self._get_connection() as connection:

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

        return [
            self._row_to_draw(row)
            for row in rows
        ]

    def get_draw_count(self) -> int:

        with self._get_connection() as connection:

            row = connection.execute(
                "SELECT COUNT(*) AS count FROM draws"
            ).fetchone()

        return int(row["count"])

    # ---------------------------------------------------------
    # Predictions
    # ---------------------------------------------------------

    def insert_prediction(
        self,
        prediction: Dict[str, Any],
    ) -> bool:

        primary = sorted(
            set(prediction["predicted_primary"])
        )

        euro = sorted(
            set(prediction["predicted_euro"])
        )

        if len(primary) != 3:
            raise ValueError(
                "Prediction must contain exactly 3 main numbers."
            )

        if len(euro) != 1:
            raise ValueError(
                "Prediction must contain exactly 1 Joker number."
            )

        with self._get_connection() as connection:

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO predictions
                (
                    prediction_date,
                    for_draw_date,
                    model_name,
                    predicted_primary,
                    predicted_euro
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    prediction.get(
                        "prediction_date",
                        datetime.utcnow().strftime("%Y-%m-%d"),
                    ),
                    prediction["for_draw_date"],
                    prediction.get(
                        "model_name",
                        "composite_frequency_delay",
                    ),
                    json.dumps(primary),
                    json.dumps(euro),
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

    def save_prediction(
        self,
        for_draw_date: str,
        primary_numbers: List[int],
        euro_numbers: List[int],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:

        metadata = metadata or {}

        prediction = {
            "prediction_date": datetime.utcnow().strftime(
                "%Y-%m-%d"
            ),
            "for_draw_date": for_draw_date,
            "model_name": metadata.get(
                "method",
                "composite_frequency_delay",
            ),
            "predicted_primary": primary_numbers,
            "predicted_euro": euro_numbers,
        }

        return self.insert_prediction(prediction)

    def prediction_exists(
        self,
        draw_date: str,
    ) -> bool:

        with self._get_connection() as connection:

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

    def get_predictions(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:

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

        parameters = ()

        if limit is not None:
            sql += " LIMIT ?"
            parameters = (limit,)

        with self._get_connection() as connection:

            rows = connection.execute(
                sql,
                parameters,
            ).fetchall()

        return [
            self._row_to_prediction(row)
            for row in rows
        ]

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _decode_numbers(value: Any) -> List[int]:

        if isinstance(value, str):

            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []

        if not isinstance(value, list):
            return []

        return [
            int(number)
            for number in value
        ]

    @classmethod
    def _row_to_draw(
        cls,
        row: sqlite3.Row,
    ) -> Dict[str, Any]:

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
```
