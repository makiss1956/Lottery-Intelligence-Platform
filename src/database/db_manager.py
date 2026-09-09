


@pytest.fixture
def test_db():
    """Fixture που δημιουργεί τη βάση και όλους τους πίνακες στη μνήμη."""
    return DBManager(db_path=":memory:")


def test_insert_prediction_success(test_db):
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9],
    }
    assert test_db.insert_prediction(prediction) is True


def test_insert_prediction_duplicate(test_db):
    prediction = {
        "prediction_date": "2026-09-09",
        "for_draw_date": "2026-09-11",
        "model_name": "markov_chain_v1",
        "predicted_primary": [5, 12, 23, 34, 45, 46, 47],
        "predicted_euro": [3, 8, 9],
    }
    assert test_db.insert_prediction(prediction) is True
    assert test_db.insert_prediction(prediction) is False


def test_prediction_exists(test_db):
    draw_date = "2026-09-11"
    assert test_db.prediction_exists(draw_date) is False

    test_db.insert_prediction({
        "prediction_date": "2026-09-09",
        "for_draw_date": draw_date,
        "model_name": "lstm_model",
        "predicted_primary": [1, 2, 3, 4, 5, 6, 7],
        "predicted_euro": [1, 2, 3],
    })
    assert test_db.prediction_exists(draw_date) is True


def test_insert_draw_success(test_db):
    draw = {
        "draw_date": "2026-09-11",
        "primary_numbers": [5, 12, 23, 34, 45],
        "euro_numbers": [3, 8],
    }
    assert test_db.insert_draw(draw) is True
    assert test_db.get_draw_count() == 1
