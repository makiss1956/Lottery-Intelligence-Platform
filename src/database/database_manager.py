
"""
SQLite Database Manager with transaction support and connection pooling.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger("DatabaseManager")


class DatabaseManager:
    """Manages SQLite connections, schema initialization, and CRUD operations."""

    def __init__(self, db_path: Optional[str] = None):
        self.config = get_config()
        self.db_path = db_path or self.config.database_path
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self):
        """Context manager for safe connection handling with transactions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
            logger.debug("Transaction committed successfully.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            conn.close()

    def initialize_database(self) -> None:
        """Creates tables if they do not exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS eurojackpot_draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_date TEXT NOT NULL UNIQUE,
            num1 INTEGER NOT NULL,
            num2 INTEGER NOT NULL,
            num3 INTEGER NOT NULL,
            num4 INTEGER NOT NULL,
            num5 INTEGER NOT NULL,
            euro1 INTEGER NOT NULL,
            euro2 INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_draw_date ON eurojackpot_draws(draw_date);
        """
        with self._connection() as conn:
            conn.executescript(schema)
            logger.info("Database initialized successfully.")

    def insert_draw(self, draw: Dict[str, Any]) -> bool:
        """Insert a single draw with transaction safety."""
        query = """
        INSERT OR IGNORE INTO eurojackpot_draws 
        (draw_date, num1, num2, num3, num4, num5, euro1, euro2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        numbers = draw.get("numbers", [])
        euro_numbers = draw.get("euro_numbers", [])
        
        if len(numbers) != 5 or len(euro_numbers) != 2:
            logger.warning(f"Invalid draw format: {draw}")
            return False

        try:
            with self._connection() as conn:
                conn.execute(query, (
                    draw.get("draw_date"),
                    numbers[0], numbers[1], numbers[2], numbers[3], numbers[4],
                    euro_numbers[0], euro_numbers[1],
                ))
            logger.info(f"Inserted draw for {draw.get('draw_date')}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert draw: {e}")
            return False

    def insert_draws(self, draws: List[Dict[str, Any]]) -> int:
        """Batch insert with single transaction."""
        if not draws:
            return 0
        
        query = """
        INSERT OR IGNORE INTO eurojackpot_draws 
        (draw_date, num1, num2, num3, num4, num5, euro1, euro2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        inserted = 0
        
        try:
            with self._connection() as conn:
                for draw in draws:
                    numbers = draw.get("numbers", [])
                    euro_numbers = draw.get("euro_numbers", [])
                    if len(numbers) == 5 and len(euro_numbers) == 2:
                        conn.execute(query, (
                            draw.get("draw_date"),
                            numbers[0], numbers[1], numbers[2], numbers[3], numbers[4],
                            euro_numbers[0], euro_numbers[1],
                        ))
                        inserted += 1
            logger.info(f"Batch inserted {inserted}/{len(draws)} draws.")
            return inserted
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            return 0

    def fetch_all(self, query: str, params: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        """Execute SELECT and return all rows."""
        try:
            with self._connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_latest_draws(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return latest draws as dictionaries."""
        query = """
        SELECT draw_date, num1, num2, num3, num4, num5, euro1, euro2
        FROM eurojackpot_draws
        ORDER BY draw_date DESC
        LIMIT ?
        """
        rows = self.fetch_all(query, (limit,))
        return [
            {
                "draw_date": row[0],
                "numbers": list(row[1:6]),
                "euro_numbers": list(row[6:8]),
            }
            for row in rows
        ]

    def get_draw_count(self) -> int:
        """Return total number of stored draws."""
        rows = self.fetch_all("SELECT COUNT(*) FROM eurojackpot_draws")
        return rows[0][0] if rows else 0
