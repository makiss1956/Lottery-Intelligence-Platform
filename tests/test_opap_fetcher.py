#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Δοκιμές για τον λήπτη δεδομένων Eurojackpot
"""

import pytest
from unittest.mock import patch, MagicMock
from src.importers.web_scraper import EurojackpotWebScraper


def test_fetch_latest_draw_success():
    """Η πιο πρόσφατη κλήρωση αναλύεται σωστά από την απάντηση του ΟΠΑΠ."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [
        {
            "drawId": 12345,
            "drawTime": 1776283200000,
            "winningNumbers": {
                "list": [5, 12, 18, 33, 45],
                "sideLists": {
                    "1": {
                        "list": [3, 9]
                    }
                }
            }
        }
    ]

    with patch(
        "requests.Session.get",
        return_value=mock_response,
    ):
        scraper = EurojackpotWebScraper()
        # ✅ Χρήση σωστής μεθόδου που υπάρχει στην κλάση
        result = scraper.fetch_recent_draws(limit=1)
        
        assert len(result) == 1
        draw = result[0]
        assert draw["main_numbers"] == [5, 12, 18, 33, 45]
        assert draw["extra_numbers"] == [3, 9]


def test_invalid_draw_is_rejected():
    """Κλήρωση με λανθασμένους αριθμούς απορρίπτεται."""
    scraper = EurojackpotWebScraper()
    
    # Αριθμός εκτός ορίων
    bad_draw = {
        "drawTime": 1776283200000,
        "winningNumbers": {
            "list": [5, 99, 18, 33, 45],  # 99 εκτός ορίου 1-50
            "sideLists": {
                "1": {"list": [3, 9]}
            }
        }
    }
    
    result = scraper._parse_draw(bad_draw)
    assert result is None


def test_valid_draw_parser():
    """Έγκυρη κλήρωση μετατρέπεται σωστά σε τυπική μορφή."""
    scraper = EurojackpotWebScraper()
    
    raw_draw = {
        "drawTime": 1776283200000,
        "winningNumbers": {
            "list": [45, 12, 33, 5, 18],
            "sideLists": {
                "1": {
                    "list": [9, 3]
                }
            }
        }
    }

    result = scraper._parse_draw(raw_draw)
    
    # ✅ Δεν πρέπει να είναι None
    assert result is not None
    
    # Επαλήθευση δομής — οι αριθμοί ταξινομούνται
    assert sorted(result["main_numbers"]) == [5, 12, 18, 33, 45]
    assert sorted(result["extra_numbers"]) == [3, 9]
    assert "draw_date" in result
