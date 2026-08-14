"""
Unit tests for the PatternAnalyzer module.
"""

import pytest
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.database.db_manager import DBManager


@pytest.fixture
def test_db_manager(tmp_path):
    """Fixture providing a temporary database populated with mock draw data."""
    db_file = tmp_path / "test_patterns.db"
    db_mgr = DBManager(db_path=str(db_file))
    db_mgr.initialize_database()

    sample_draws = [
        {"draw_date": "2026-03-01", "primary_numbers": [5, 12, 23, 34, 45], "euro_numbers": [2, 7]},
        {"draw_date": "2026-03-05", "primary_numbers": [2, 4, 6, 8, 10], "euro_numbers": [1, 3]},
    ]
    for draw in sample_draws:
        db_mgr.insert_draw(draw)

    return db_mgr


def test_odd_even_distribution(test_db_manager):
    """Verify correct counting of odd and even numbers in draws."""
    analyzer = PatternAnalyzer(test_db_manager)
    distribution = analyzer.analyze_odd_even_distribution()

    assert distribution.get("3_odd_2_even") == 1
    assert distribution.get("0_odd_5_even") == 1


def test_high_low_distribution(test_db_manager):
    """Verify correct classification of low vs high numbers."""
    analyzer = PatternAnalyzer(test_db_manager)
    distribution = analyzer.analyze_high_low_distribution(cutoff=25)

    assert distribution.get("3_low_2_high") == 1
    assert distribution.get("5_low_0_high") == 1


def test_sum_ranges(test_db_manager):
    """Verify sum statistics calculation (min, max, average)."""
    analyzer = PatternAnalyzer(test_db_manager)
    stats = analyzer.analyze_sum_ranges()

    assert stats["min_sum"] == 30
    assert stats["max_sum"] == 119
    assert stats["avg_sum"] == 74.5
    assert stats["total_analyzed"] == 2
