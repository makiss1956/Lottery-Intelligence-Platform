"""
Unit tests for the PatternAnalyzer module.
"""

import pytest
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.database.database_manager import DatabaseManager


@pytest.fixture
def test_db_manager(tmp_path):
    """Fixture providing a temporary database populated with mock draw data."""
    db_file = tmp_path / "test_patterns.db"
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

    # Draw 1: [5, 12, 23, 34, 45] -> Odds: 5, 23, 45 (3) | Evens: 12, 34 (2) | Sum: 119
    # Draw 2: [2, 4, 6, 8, 10]    -> Odds: 0          | Evens: 5          | Sum: 30
    sample_draws = [
        ("2026-03-01", 5, 12, 23, 34, 45, 2, 7),
        ("2026-03-05", 2, 4, 6, 8, 10, 1, 3),
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

    # Draw 1: [5, 12, 23] <= 25 (3 Low), [34, 45] > 25 (2 High)
    # Draw 2: [2, 4, 6, 8, 10] <= 25 (5 Low)
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
