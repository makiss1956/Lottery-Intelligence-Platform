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
    db_mgr.initialize_database()
    return db_mgr


def test_insert_prediction_success(test_db):
    """Έλεγχος επιτυχούς εισαγωγής πρόβλεψης."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23],
        "predicted_euro": [3],
    }
    assert test_db.insert_prediction(prediction) is True


def test_insert_prediction_duplicate(test_db):
    """Έλεγχος αποτροπής διπλότυπης εγγραφής πρόβλεψης."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23],
        "predicted_euro": [3],
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
        "predicted_primary": [5, 12, 23],
        "predicted_euro": [3],
    }
    test_db.insert_prediction(prediction)
    assert test_db.prediction_exists(draw_date) is True


def test_get_predictions(test_db):
    """Έλεγχος ανάκτησης λίστας προβλέψεων."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23],
        "predicted_euro": [3],
    }
    test_db.insert_prediction(prediction)
    predictions = test_db.get_predictions(limit=10)
    assert len(predictions) == 1
    assert predictions[0]["for_draw_date"] == "2026-09-11"


def test_save_prediction_helper(test_db):
    """Έλεγχος της μεθόδου save_prediction που χρησιμοποιεί το main pipeline."""
    saved = test_db.save_prediction(
        for_draw_date="2026-09-15",
        primary_numbers=[1, 2, 3],
        euro_numbers=[4],
        metadata={"method": "composite_frequency_delay"},
    )
    assert saved is True
    assert test_db.prediction_exists("2026-09-15") is True


def test_insert_draw_success(test_db):
    """Έλεγχος επιτυχούς εισαγωγής αποτελέσματος κλήρωσης."""
    draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [5, 12, 23, 34, 45],
        "euro_numbers": [3, 8],
    }
    assert test_db.insert_draw(draw) is True
    assert test_db.get_draw_count() == 1


def test_insert_draw_duplicate(test_db):
    """Έλεγχος αποτροπής διπλότυπης εισαγωγής κλήρωσης."""
    draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [5, 12, 23, 34, 45],
        "euro_numbers": [3, 8],
    }
    assert test_db.insert_draw(draw) is True
    assert test_db.insert_draw(draw) is False
    assert test_db.get_draw_count() == 1


def test_get_latest_draw(test_db):
    """Έλεγχος ανάκτησης της πιο πρόσφατης κλήρωσης."""
    draw1 = {
        "draw_date": "2026-09-01",
        "primary_numbers": [1, 2, 3, 4, 5],
        "euro_numbers": [1, 2],
    }
    draw2 = {
        "draw_date": "2026-09-05",
        "primary_numbers": [10, 20, 30, 40, 50],
        "euro_numbers": [3, 4],
    }
    test_db.insert_draw(draw1)
    test_db.insert_draw(draw2)

    latest = test_db.get_latest_draw()
    assert latest is not None
    assert latest["draw_date"] == "2026-09-05"
    assert latest["primary_numbers"] == [10, 20, 30, 40, 50]
