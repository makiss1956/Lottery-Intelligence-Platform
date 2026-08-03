"""
Unit tests for the Analytics Engine modules:
FrequencyAnalyzer, ProbabilityPredictor, and Backtester.
"""

import os
import sqlite3
import pytest

from src.analytics.backtester import Backtester
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.database.database_manager import DatabaseManager


@pytest.fixture
def test_db_manager(tmp_path):
    """Fixture providing a temporary SQLite database pre-populated with mock draw data."""
    db_file = tmp_path / "test_analytics.db"
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

    # Insert 3 sample draws
    sample_draws = [
        ("2026-03-01", 5, 12, 23, 34, 45, 2, 7),
        ("2026-03-05", 5, 10, 15, 20, 25, 2, 9),
        ("2026-03-10", 1, 2, 3, 4, 5, 1, 2),
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


def test_frequency_analyzer_counts(test_db_manager):
    """Verify that frequency calculations accurately aggregate number occurrences."""
    analyzer = FrequencyAnalyzer(test_db_manager)
    freqs = analyzer.calculate_number_frequencies()
    euro_freqs = analyzer.calculate_euro_frequencies()

    # Number 5 appears in all 3 draws
    assert freqs[5] == 3
    # Number 12 appears in 1 draw
    assert freqs[12] == 1
    # Number 50 appears in 0 draws
    assert freqs[50] == 0

    # Euro number 2 appears in 3 draws
    assert euro_freqs[2] == 3


def test_predictor_candidate_counts(test_db_manager):
    """Ensure prediction output contains exactly requested candidate set sizes."""
    analyzer = FrequencyAnalyzer(test_db_manager)
    predictor = ProbabilityPredictor(analyzer)

    candidates = predictor.predict_candidate_set(primary_count=7, euro_count=3)

    assert len(candidates["primary_candidates"]) == 7
    assert len(candidates["euro_candidates"]) == 3
    assert len(set(candidates["primary_candidates"])) == 7  # All unique


def test_backtester_evaluation():
    """Verify that backtester correctly calculates hits and target metrics."""
    predicted_mains = [1, 2, 3, 10, 20, 30, 40]
    predicted_euros = [1, 2, 5]

    actual_draw = {
        "draw_date": "2026-03-10",
        "numbers": [1, 2, 3, 4, 5],
        "euro_numbers": [1, 2],
    }

    result = Backtester.evaluate_prediction(predicted_mains, predicted_euros, actual_draw)

    # Should match numbers 1, 2, 3 -> 3 hits
    assert result["main_hits_count"] == 3
    assert result["euro_hits_count"] == 2
    assert result["target_achieved"] is True
