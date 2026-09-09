import pytest
import sqlite3

# Import your DBManager class according to your project path
from src.database.db_manager import DBManager


@pytest.fixture
def test_db():
    """
    Fixture initializing an in-memory SQLite database instance
    and constructing the required tables for tests.
    """
    db_mgr = DBManager(db_path=":memory:")
    
    # Enable row factory if your manager relies on dict-like row access
    db_mgr.conn.row_factory = sqlite3.Row
    
    # Initialize full schema
    with db_mgr.conn:
        db_mgr.conn.executescript("""
            CREATE TABLE IF NOT EXISTS eurojackpot_draws (
                draw_date TEXT PRIMARY KEY,
                primary_numbers TEXT NOT NULL,
                euro_numbers TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_draw_date TEXT NOT NULL,
                model_name TEXT NOT NULL,
                predicted_primary TEXT NOT NULL,
                predicted_euro TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_validated INTEGER DEFAULT 0,
                matched_primary INTEGER,
                matched_euro INTEGER,
                UNIQUE(target_draw_date, model_name)
            );
        """)
    return db_mgr


def test_insert_prediction_success(test_db):
    """Test successful insertion of a new prediction entry."""
    prediction = {
        "target_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45],
        "predicted_euro": [3, 9]
    }
    
    inserted = test_db.insert_prediction(prediction)
    assert inserted is True
    assert test_db.prediction_exists("2026-09-11", "markov_chain_v1") is True


def test_insert_prediction_duplicate(test_db):
    """Test that inserting a duplicate (target_draw_date, model_name) fails or is ignored."""
    prediction = {
        "target_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45],
        "predicted_euro": [3, 9]
    }
    
    first_attempt = test_db.insert_prediction(prediction)
    second_attempt = test_db.insert_prediction(prediction)
    
    assert first_attempt is True
    assert second_attempt is False


def test_prediction_exists(test_db):
    """Test checking existence of non-existent vs existent predictions."""
    assert test_db.prediction_exists("2026-09-11", "lstm_model") is False
    
    test_db.insert_prediction({
        "target_draw_date": "2026-09-11",
        "model_name": "lstm_model",
        "predicted_primary": [1, 2, 3, 4, 5],
        "predicted_euro": [1, 2]
    })
    
    assert test_db.prediction_exists("2026-09-11", "lstm_model") is True
    assert test_db.prediction_exists("2026-09-11", "non_existent_model") is False


def test_validate_prediction_for_draw_full_match(test_db):
    """Test validation with a 5+2 exact hit."""
    draw_date = "2026-09-11"
    
    # 1. Insert Actual Draw
    test_db.insert_draw({
        "draw_date": draw_date,
        "primary_numbers": [5, 12, 23, 34, 45],
        "euro_numbers": [3, 9]
    })
    
    # 2. Insert Prediction
    test_db.insert_prediction({
        "target_draw_date": draw_date,
        "model_name": "oracle_v1",
        "predicted_primary": [5, 12, 23, 34, 45],
        "predicted_euro": [3, 9]
    })
    
    # 3. Validate
    updated_count = test_db.validate_prediction_for_draw(draw_date)
    assert updated_count == 1
    
    # Verify validation results
    cursor = test_db.conn.cursor()
    row = cursor.execute(
        "SELECT is_validated, matched_primary, matched_euro FROM predictions WHERE target_draw_date = ?", 
        (draw_date,)
    ).fetchone()
    
    assert row["is_validated"] == 1
    assert row["matched_primary"] == 5
    assert row["matched_euro"] == 2


def test_validate_prediction_for_draw_partial_match(test_db):
    """Test validation with a partial match (3 primary numbers, 1 euro number)."""
    draw_date = "2026-09-11"
    
    test_db.insert_draw({
        "draw_date": draw_date,
        "primary_numbers": [10, 20, 30, 40, 50],
        "euro_numbers": [1, 10]
    })
    
    test_db.insert_prediction({
        "target_draw_date": draw_date,
        "model_name": "stats_engine",
        "predicted_primary": [10, 20, 30, 1, 2],  # Matches 10, 20, 30
        "predicted_euro": [1, 12]                 # Matches 1
    })
    
    test_db.validate_prediction_for_draw(draw_date)
    
    cursor = test_db.conn.cursor()
    row = cursor.execute(
        "SELECT is_validated, matched_primary, matched_euro FROM predictions WHERE target_draw_date = ?", 
        (draw_date,)
    ).fetchone()
    
    assert row["is_validated"] == 1
    assert row["matched_primary"] == 3
    assert row["matched_euro"] == 1


def test_validate_prediction_missing_draw(test_db):
    """Test validation attempt when the corresponding draw date does not exist in DB."""
    draw_date = "2026-09-11"
    
    test_db.insert_prediction({
        "target_draw_date": draw_date,
        "model_name": "orphan_prediction",
        "predicted_primary": [1, 2, 3, 4, 5],
        "predicted_euro": [1, 2]
    })
    
    updated_count = test_db.validate_prediction_for_draw(draw_date)
    assert updated_count == 0  # No draw available to validate against
