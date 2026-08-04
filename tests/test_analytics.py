"""
Unit tests for frequency analysis, prediction, and backtesting engines.
"""

import pytest
from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.database.database_manager import DatabaseManager


@pytest.fixture
def test_db_manager(tmp_path):
    """Fixture providing a temporary database populated with mock draw data."""
    db_file = tmp_path / "test_lottery.db"
    schema_content = """
    CREATE TABLE IF NOT EXISTS eurojackpot_draws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draw_date TEXT UNIQUE NOT NULL,
        num1 INTEGER NOT NULL,
        num2 INTEGER NOT NULL,
        num3 INTEGER NOT NULL,
        num4 INTEGER NOT NULL,
        num5 INTEGER NOT NULL,
        euro1 INTEGER NOT NULL,
        euro2 INTEGER NOT NULL
    );
    """
    schema_file = tmp_path / "schema.sql"
    schema_file.write_text(schema_content)

    db_mgr = DatabaseManager(db_path=str(db_file), schema_path=str(schema_file))
    db_mgr.initialize_database()

    # Populate mock draws
    sample_draws = [
        ("2026-01-01", 1, 2, 3, 4, 5, 1, 2),
        ("2026-01-05", 1, 2, 3, 10, 11, 1, 3),
        ("2026-01-10", 1, 2, 15, 16, 17, 2, 4),
    ]
    for draw in sample_draws:
        db_mgr.execute(
            """
            INSERT INTO eurojackpot_draws (draw_date, num1, num2, num3, num4, num5, euro1, euro2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            draw,
        )

    return db_mgr


def test_frequency_analyzer(test_db_manager):
    """Verify frequency count calculations for primary and euro numbers."""
    analyzer = FrequencyAnalyzer(test_db_manager)
    primary_freqs = analyzer.get_primary_frequencies()
    euro_freqs = analyzer.get_euro_frequencies()

    # Numbers 1 and 2 appear in all 3 draws
    assert primary_freqs[1] == 3
    assert primary_freqs[2] == 3
    # Euro number 1 appears in 2 draws
    assert euro_freqs[1] == 2


def test_probability_predictor_without_pattern(test_db_manager):
    """Verify standard candidate set selection based purely on frequency."""
    freq_analyzer = FrequencyAnalyzer(test_db_manager)
    predictor = ProbabilityPredictor(freq_analyzer)

    candidates = predictor.predict_candidate_set(primary_count=5, euro_count=2)

    assert len(candidates["primary_candidates"]) == 5
    assert len(candidates["euro_candidates"]) == 2
    # Most frequent primary numbers 1 and 2 must be included
    assert 1 in candidates["primary_candidates"]
    assert 2 in candidates["primary_candidates"]


def test_probability_predictor_with_pattern_analyzer(test_db_manager):
    """Verify candidate set generation with integrated PatternAnalyzer optimization."""
    freq_analyzer = FrequencyAnalyzer(test_db_manager)
    pattern_analyzer = PatternAnalyzer(test_db_manager)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer=pattern_analyzer)

    candidates = predictor.predict_candidate_set(primary_count=5, euro_count=2)

    assert len(candidates["primary_candidates"]) == 5
    assert len(candidates["euro_candidates"]) == 2
    # Ensure candidates list is sorted after optimization
    assert candidates["primary_candidates"] == sorted(candidates["primary_candidates"])


def test_backtester(test_db_manager):
    """Verify evaluation metric outputs from the backtesting engine."""
    freq_analyzer = FrequencyAnalyzer(test_db_manager)
    predictor = ProbabilityPredictor(freq_analyzer)
    backtester = Backtester(test_db_manager, predictor)

    results = backtester.run_evaluations(eval_draws=2)

    assert results["total_evaluated"] == 2
    assert "average_primary_matches" in results
    assert "average_euro_matches" in results
