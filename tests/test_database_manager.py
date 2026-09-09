"""
Unit tests for DBManager.
"""

import pytest
from src.database.db_manager import DBManager


@pytest.fixture
def test_db(tmp_path):
    """Fixture που παρέχει μια προσωρινή βάση δεδομένων σε αρχείο."""
    db_file = tmp_path / "test_db_manager.db"
    db_mgr = DBManager(db_path=str(db_file))
    return db_mgr


def test_insert_prediction_success(test_db):
    """Έλεγχος επιτυχούς εισαγωγής πρόβλεψης."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9],
    }
    assert test_db.insert_prediction(prediction) is True


def test_insert_prediction_duplicate(test_db):
    """Έλεγχος αποτροπής διπλότυπης εγγραφής πρόβλεψης."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9],
    }
    assert test_db.insert_prediction(prediction) is True
    # Η δεύτερη εισαγωγή με το ίδιο for_draw_date πρέπει να αποτύχει
    assert test_db.insert_prediction(prediction) is False


def test_prediction_exists(test_db):
    """Έλεγχος ύπαρξης πρόβλεψης για συγκεκριμένη ημερομηνία κλήρωσης."""
    draw_date = "2026-09-11"
    assert test_db.prediction_exists(draw_date) is False

    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": draw_date,
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9],
    }
    test_db.insert_prediction(prediction)
    assert test_db.prediction_exists(draw_date) is True


def test_insert_draw_success(test_db):
    """Έλεγχος επιτυχούς εισαγωγής αποτελέσματος κλήρωσης."""
    draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [5, 12, 23, 34, 45],
        "euro_numbers": [3, 8],
    }
    assert test_db.insert_draw(draw) is True
    assert test_db.get_draw_count() == 1
