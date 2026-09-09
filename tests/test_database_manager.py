import pytest
from src.database.db_manager import DBManager


@pytest.fixture
def test_db():
    """
    Fixture που αρχικοποιεί ένα in-memory SQLite DBManager instance.
    Το DBManager αναλαμβάνει αυτόματα τη δημιουργία του schema.
    """
    return DBManager(db_path=":memory:")


def test_insert_prediction_success(test_db):
    """Έλεγχος επιτυχούς εισαγωγής νέας πρόβλεψης."""
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
    """Έλεγχος διαχείρισης διπλότυπης εγγραφής (target_draw_date, model_name)."""
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
    """Έλεγχος ύπαρξης πρόβλεψης στη βάση."""
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
    """Έλεγχος επαλήθευσης πρόβλεψης με πλήρη επιτυχία 5+2."""
    draw_date = "2026-09-11"
    
    test_db.insert_draw({
        "draw_date": draw_date,
        "primary_numbers": [5, 12, 23, 34, 45],
        "euro_numbers": [3, 9]
    })
    
    test_db.insert_prediction({
        "target_draw_date": draw_date,
        "model_name": "oracle_v1",
        "predicted_primary": [5, 12, 23, 34, 45],
        "predicted_euro": [3, 9]
    })
    
    updated_count = test_db.validate_prediction_for_draw(draw_date)
    assert updated_count >= 1


def test_validate_prediction_for_draw_partial_match(test_db):
    """Έλεγχος επαλήθευσης πρόβλεψης με μερική επιτυχία."""
    draw_date = "2026-09-11"
    
    test_db.insert_draw({
        "draw_date": draw_date,
        "primary_numbers": [10, 20, 30, 40, 50],
        "euro_numbers": [1, 10]
    })
    
    test_db.insert_prediction({
        "target_draw_date": draw_date,
        "model_name": "stats_engine",
        "predicted_primary": [10, 20, 30, 1, 2],
        "predicted_euro": [1, 12]
    })
    
    updated_count = test_db.validate_prediction_for_draw(draw_date)
    assert updated_count >= 1


def test_validate_prediction_missing_draw(test_db):
    """Έλεγχος προσπάθειας επαλήθευσης όταν δεν υπάρχει καταγεγραμμένη κλήρωση."""
    draw_date = "2026-09-11"
    
    test_db.insert_prediction({
        "target_draw_date": draw_date,
        "model_name": "orphan_prediction",
        "predicted_primary": [1, 2, 3, 4, 5],
        "predicted_euro": [1, 2]
    })
    
    updated_count = test_db.validate_prediction_for_draw(draw_date)
    assert updated_count == 0
