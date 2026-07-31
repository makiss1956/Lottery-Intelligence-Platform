"""
Lottery Intelligence Platform
Database Manager

Handles SQLite database connections.
"""

import sqlite3
from pathlib import Path


class DatabaseManager:

    def __init__(self, db_name="lottery.db"):
        self.db_path = Path("database") / db_name

    def connect(self):
        return sqlite3.connect(self.db_path)

    def execute(self, sql, params=None):

        conn = self.connect()
        cursor = conn.cursor()

        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        conn.commit()
        conn.close()

    def fetch_all(self, sql):

        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(sql)

        rows = cursor.fetchall()

        conn.close()

        return rows
