import pytest
from src.database.db_manager import DBManager


@pytest.fixture
def test_db():
    """Fixture που αρχικοποιεί το DBManager instance."""
    db_mgr = DBManager(db_path=":memory:")  # In-memory database για τεστ
    # Αφαιρέθηκε η κλήση σε init_db() που δεν υπάρχει
    return db_mgr


def test_insert_prediction_success(test_db):
    """Έλεγχος επιτυχούς εισαγωγής νέας πρόβλεψης με 7 κύριους και 3 euro αριθμούς."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9]
    }
    
    inserted = test_db.insert_prediction(prediction)
    assert inserted is True


def test_insert_prediction_duplicate(test_db):
    """Έλεγχος διαχείρισης διπλότυπης εγγραφής."""
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9]
    }
    
    first_attempt = test_db.insert_prediction(prediction)
    second_attempt = test_db.insert_prediction(prediction)
    
    assert first_attempt is True
    assert second_attempt is False


def test_prediction_exists(test_db):
    """Έλεγχος ύπαρξης πρόβλεψης στη βάση."""
    draw_date = "2026-09-11"
    
    assert test_db.prediction_exists(draw_date) is False
    
    test_db.insert_prediction({
        "prediction_date": "2026-09-09",
        "for_draw_date": draw_date,
        "model_name": "lstm_model",
        "predicted_primary": [1, 2, 3, 4, 5, 6, 7],
        "predicted_euro": [1, 2, 3]
    })
    
    assert test_db.prediction_exists(draw_date) is True


def test_validate_prediction_for_draw_full_match(test_db):
    """Έλεγχος επαλήθευσης πρόβλεψης."""
    actual_draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [5, 12, 23, 34, 45, 46, 47],
        "euro_numbers": [3, 8, 9]
    }
    
    test_db.insert_prediction({
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "oracle_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9]
    })
    
    result = test_db.validate_prediction_for_draw(actual_draw)
    assert result is not None


def test_validate_prediction_for_draw_partial_match(test_db):
    """Έλεγχος επαλήθευσης πρόβλεψης με μερική επιτυχία."""
    actual_draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [10, 20, 30, 40, 50, 6, 7],
        "euro_numbers": [1, 2, 10]
    }
    
    test_db.insert_prediction({
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "stats_engine",
        "predicted_primary": [10, 20, 30, 1, 2, 3, 4],
        "predicted_euro": [1, 2, 12]
    })
    
    result = test_db.validate_prediction_for_draw(actual_draw)
    assert result is not None


def test_validate_prediction_missing_draw(test_db):
    """Έλεγχος προσπάθειας επαλήθευσης όταν η κλήρωση δεν περιέχει στοιχεία."""
    empty_draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [],
        "euro_numbers": []
    }
    
    test_db.insert_prediction({
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "orphan_prediction",
        "predicted_primary": [1, 2, 3, 4, 5, 6, 7],
        "predicted_euro": [1, 2, 3]
    })
    
    result = test_db.validate_prediction_for_draw(empty_draw)
    assert result is not None or result == {}
