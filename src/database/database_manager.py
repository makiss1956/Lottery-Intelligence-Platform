"""
Database Manager Module
----------------------
Handles database connections, schema execution, draw persistence, 
batch insertions with transaction management, and query operations.
"""

import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple, TypedDict

logger = logging.getLogger(__name__)


class BatchResult(TypedDict):
    inserted_count: int
    skipped_count: int
    success: bool


class DBManager:
    """Manages SQLite database operations with batching and transaction safety."""

    def __init__(self, db_path: str = "lottery_data.db"):
        """
        Initialize database connection manager.

        :param db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Creates and returns a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database schema if tables do not exist."""
        query = """
        CREATE TABLE IF NOT EXISTS draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_number INTEGER UNIQUE NOT NULL,
            draw_date TEXT,
            winning_numbers TEXT NOT NULL,
            bonus_numbers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.get_connection() as conn:
                conn.execute(query)
                conn.commit()
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize database schema: %s", e)
            raise

    def save_draw_if_new(self, draw: Dict[str, Any]) -> bool:
        """
        Saves a draw only if it does not already exist in the database.

        :param draw: Dictionary containing draw data.
        :return: True if the draw was inserted, False if it already existed.
        """
        return self.insert_draw(draw)

    def insert_draw(self, draw: Dict[str, Any]) -> bool:
        """
        Inserts a single draw record with uniqueness validation.

        :param draw: Dictionary containing draw data.
        :return: True if newly inserted, False if skipped/duplicate.
        """
        result = self.insert_draws([draw], batch_size=1)
        return result["inserted_count"] > 0

    def insert_draws(self, draws: List[Dict[str, Any]], batch_size: int = 100) -> BatchResult:
        """
        Inserts a list of draws using chunked batch transactions.
        Commits every N records (batch_size) to ensure partial success on failure.

        :param draws: List of draw dictionaries.
        :param batch_size: Number of records per transaction commit.
        :return: BatchResult dictionary with inserted_count, skipped_count, and success flag.
        """
        if not draws:
            return {"inserted_count": 0, "skipped_count": 0, "success": True}

        query = """
        INSERT OR IGNORE INTO draws (draw_number, draw_date, winning_numbers, bonus_numbers)
        VALUES (?, ?, ?, ?);
        """

        total_inserted = 0
        total_skipped = 0
        has_error = False

        # Διαχωρισμός των εγγραφών σε batches (chunking)
        for i in range(0, len(draws), batch_size):
            batch = draws[i:i + batch_size]
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    batch_inserted = 0
                    
                    for draw in batch:
                        draw_number = draw.get("draw_number")
                        draw_date = str(draw.get("draw_date", ""))
                        
                        # Μετατροπή λιστών σε string αν χρειάζεται
                        primaries = draw.get("primary_numbers") or draw.get("winning_numbers") or []
                        euros = draw.get("euro_numbers") or draw.get("bonus_numbers") or []
                        
                        winning_str = ",".join(map(str, primaries)) if isinstance(primaries, list) else str(primaries)
                        bonus_str = ",".join(map(str, euros)) if isinstance(euros, list) else str(euros)

                        cursor.execute(query, (draw_number, draw_date, winning_str, bonus_str))
                        if cursor.rowcount > 0:
                            batch_inserted += 1

                    conn.commit()  # Commit ανά batch
                    total_inserted += batch_inserted
                    total_skipped += (len(batch) - batch_inserted)

            except Exception as e:
                logger.error("Error inserting batch starting at index %d: %s", i, e)
                has_error = True
                total_skipped += len(batch)

        logger.info("Batch insertion finished. Inserted: %d, Skipped: %d", total_inserted, total_skipped)

        return {
            "inserted_count": total_inserted,
            "skipped_count": total_skipped,
            "success": not has_error
        }

    def get_all_draws(self) -> List[Dict[str, Any]]:
        """
        Retrieves all stored draws ordered by draw_number ascending.

        :return: List of draw dictionaries.
        """
        query = "SELECT draw_number, draw_date, winning_numbers, bonus_numbers FROM draws ORDER BY draw_number ASC;"
        draws = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                rows = cursor.execute(query).fetchall()
                for row in rows:
                    draws.append({
                        "draw_number": row["draw_number"],
                        "draw_date": row["draw_date"],
                        "primary_numbers": [int(x) for x in row["winning_numbers"].split(",") if x.isdigit()],
                        "euro_numbers": [int(x) for x in row["bonus_numbers"].split(",") if x.isdigit()] if row["bonus_numbers"] else []
                    })
        except Exception as e:
            logger.error("Failed to retrieve draws: %s", e)

        return draws
