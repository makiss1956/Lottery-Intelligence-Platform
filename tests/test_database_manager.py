import pytest
from pathlib import Path
from src.database.db_manager import DBManager

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_lottery.db"
    db_mgr = DBManager(db_path=str(db_file))
    db_mgr.initialize_database()
    return db_mgr

def test_database_initialization(test_db):
    assert Path(test_db.db_path).exists()

def test_insert_and_fetch_draw(test_db):
    draw = {
        "draw_date": "2026-01-01",
        "primary_numbers": [1, 2, 3, 4, 5],
        "euro_numbers": [1, 2]
    }
    assert test_db.insert_draw(draw) is True
    
    latest = test_db.get_latest_draws(limit=1)
    assert len(latest) == 1
    assert latest[0]["draw_date"] == "2026-01-01"
    assert latest[0]["primary_numbers"] == [1, 2, 3, 4, 5]

def test_insert_duplicate_ignored(test_db):
    draw = {
        "draw_date": "2026-01-01",
        "primary_numbers": [1, 2, 3, 4, 5],
        "euro_numbers": [1, 2]
    }
    test_db.insert_draw(draw)
    result = test_db.insert_draw(draw)
    assert test_db.get_draw_count() == 1

def test_empty_database(test_db):
    assert test_db.get_draw_count() == 0
    assert test_db.get_latest_draws(limit=10) == []
