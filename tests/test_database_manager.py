import pytest
import sqlite3
from pathlib import Path
from src.database.database_manager import DatabaseManager

def test_database_initialization(tmp_path):
    """
    Test that the database initializes and creates tables correctly.
    """
    db_file = tmp_path / "test_lottery.db"
    schema_file = tmp_path / "schema.sql"
    
    # Dummy schema for testing
    schema_file.write_text("""
        CREATE TABLE IF NOT EXISTS test_draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_date TEXT NOT NULL
        );
    """)

    db_mgr = DatabaseManager(db_path=str(db_file), schema_path=str(schema_file))
    db_mgr.initialize_database()

    assert db_file.exists()
    assert db_mgr.table_exists("test_draws")

def test_execute_and_fetch(tmp_path):
    """
    Test execution of SQL insert and fetch operations.
    """
    db_file = tmp_path / "test_lottery.db"
    db_mgr = DatabaseManager(db_path=str(db_file))
    
    db_mgr.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
    db_mgr.execute("INSERT INTO users (name) VALUES (?);", ("Makis",))
    
    result = db_mgr.fetch_one("SELECT name FROM users WHERE id = ?;", (1,))
    assert result is not None
    assert result["name"] == "Makis"
