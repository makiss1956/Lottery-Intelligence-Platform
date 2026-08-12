"""
Database Manager for Lottery Intelligence Platform.
Handles SQLite database connection, schema setup, and query execution.
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
        """Επιστρέφει σύνδεση με την SQLite βάση."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Δημιουργεί τους πίνακες αν δεν υπάρχουν ήδη."""
        schema_path = Path("src/database/schema.sql")
       
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    cursor.executescript(f.read())
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS draws (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        draw_date TEXT UNIQUE NOT NULL,
                        num1 INTEGER, num2 INTEGER, num3 INTEGER, num4 INTEGER, num5 INTEGER,
                        euro1 INTEGER, euro2 INTEGER,
                        jackpot REAL
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        target_date TEXT,
                        num1 INTEGER, num2 INTEGER, num3 INTEGER, num4 INTEGER, num5 INTEGER,
                        euro1 INTEGER, euro2 INTEGER,
                        accuracy_score REAL
                    );
                """)
            conn.commit()
        logger.info("Database initialized successfully.")

    def execute_query(self, query, params=()):
        """Εκτελεί ένα SQL query (INSERT, UPDATE, DELETE)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetch_all(self, query, params=()):
        """Επιστρέφει όλα τα αποτελέσματα μιας αναζήτησης."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def fetch_one(self, query, params=()):
        """Επιστρέφει ένα αποτέλεσμα αναζήτησης."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

# Alias για συμβατότητα σε περίπτωση που καλείται και ως DatabaseManager
DatabaseManager = DBManager
