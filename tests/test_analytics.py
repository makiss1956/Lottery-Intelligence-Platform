import pytest
from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.database.database_manager import DatabaseManager

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test.db"
    db_mgr = DatabaseManager(db_path=str(db_file))
    db_mgr.initialize_database()
    
    sample_draws = [
        {"draw_date": "2026-01-01", "numbers": [1, 2, 3, 4, 5], "euro_numbers": [1, 2]},
        {"draw_date": "2026-01-05", "numbers": [1, 2, 3, 10, 11], "euro_numbers": [1, 3]},
        {"draw_date": "2026-01-10", "numbers": [1, 2, 15, 16, 17], "euro_numbers": [2, 4]},
    ]
    for d in sample_draws:
        db_mgr.insert_draw(d)
    return db_mgr

def test_frequency_analyzer(test_db):
    analyzer = FrequencyAnalyzer(test_db)
    # ✅ ΣΩΣΤΕΣ ΜΕΘΟΔΟΙ
    primary_freqs = analyzer.calculate_number_frequencies()
    euro_freqs = analyzer.calculate_euro_frequencies()
    
    assert primary_freqs[1] == 3
    assert primary_freqs[2] == 3
    assert euro_freqs[1] == 2

def test_predictor_with_empty_db(tmp_path):
    db_mgr = DatabaseManager(db_path=str(tmp_path / "empty.db"))
    db_mgr.initialize_database()
    analyzer = FrequencyAnalyzer(db_mgr)
    predictor = ProbabilityPredictor(analyzer)
    
    # ✅ Ελέγχει safety check για κενή βάση
    candidates = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    assert candidates["primary_candidates"] == []
    assert candidates["euro_candidates"] == []

def test_backtester_static_methods():
    # ✅ Χρησιμοποιεί static methods σωστά
    result = Backtester.evaluate_prediction(
        predicted_mains=[1, 2, 3, 4, 5],
        predicted_euros=[1, 2],
        actual_draw={"draw_date": "2026-01-01", "numbers": [1, 2, 10, 20, 30], "euro_numbers": [1, 5]}
    )
    assert result["main_hits_count"] == 2
    assert result["euro_hits_count"] == 1
    assert result["target_achieved"] is False  # < 3 main hits

def test_backtester_batch():
    history = [
        {"draw_date": "2026-01-01", "main_hits_count": 3, "target_achieved": True},
        {"draw_date": "2026-01-05", "main_hits_count": 1, "target_achieved": False},
    ]
    stats = Backtester.run_batch_backtest(history)
    assert stats["total_tests"] == 2
    assert stats["success_rate_percentage"] == 50.0
