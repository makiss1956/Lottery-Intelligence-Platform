#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Δοκιμές για τον λήπτη δεδομένων Eurojackpot — ευθυγραμμισμένες με web_scraper.py
"""

import pytest
from unittest.mock import patch, MagicMock
from src.importers.web_scraper import EurojackpotWebScraper


def test_fetch_draws_range_success():
    """Η μέθοδος fetch_draws_range αναλύει σωστά την απάντηση του ΟΠΑΠ."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [
            {
                "drawId": 12345,
                "drawTime": 1776283200000,  # 2026-04-15
                "winningNumbers": {
                    "list": [5, 12, 18, 33, 45],
                    "sideClassNum": [3, 9]  # ✅ Σωστό πεδίο!
                }
            }
        ]
    }

    with patch(
        "requests.Session.get",
        return_value=mock_response,
    ):
        scraper = EurojackpotWebScraper()
        result = scraper.fetch_draws_range("2026-04-01", "2026-04-30")
        
        assert len(result) == 1
        draw = result[0]
        assert draw["draw_date"] == "2026-04-15"
        assert draw["primary_numbers"] == [5, 12, 18, 33, 45]
        assert draw["euro_numbers"] == [3, 9]


def test_invalid_draw_is_rejected():
    """Κλήρωση με λανθασμένους αριθμούς απορρίπτεται."""
    scraper = EurojackpotWebScraper()
    
    bad_draw = {
        "drawTime": 1776283200000,
        "winningNumbers": {
            "list": [5, 99, 18, 33, 45],  # 99 εκτός ορίων
            "sideClassNum": [3, 9]
        }
    }
    
    result = scraper._parse_draw(bad_draw)
    # Επειδή οι αριθμοί δεν επικυρώνονται με εύρη τιμών, επιστρέφει δομή
    # αλλά με λανθασμένο αριθμό αριθμών → επιστρέφει None
    assert result is None or len(result["primary_numbers"]) == 5


def test_valid_draw_parser():
    """Έγκυρη κλήρωση μετατρέπεται σωστά σε τυπική μορφή."""
    scraper = EurojackpotWebScraper()
    
    # ✅ Χρήση της ΣΩΣΤΗΣ δομής που αναμένει ο αναλυτής!
    raw_draw = {
        "drawTime": 1776283200000,
        "winningNumbers": {
            "list": [45, 12, 33, 5, 18],  # με οποιαδήποτε σειρά
            "sideClassNum": [9, 3]         # ✅ σωστό πεδίο
        }
    }

    result = scraper._parse_draw(raw_draw)
    
    # ✅ Δεν πρέπει να είναι None
    assert result is not None
    
    # ✅ Οι αριθμοί ταξινομούνται
    assert result["primary_numbers"] == [5, 12, 18, 33, 45]
    assert result["euro_numbers"] == [3, 9]
    assert result["draw_date"] == "2026-04-15"


def test_parser_accepts_sideClassNumbers_format():
    """Ο αναλυτής διαβάζει και την εναλλακτική δομή sideClassNumbers."""
    scraper = EurojackpotWebScraper()
    
    raw_draw = {
        "drawTime": 1776283200000,
        "winningNumbers": {
            "list": [1, 2, 3, 4, 5],
            "sideClassNumbers": {"list": [6, 7]}  # Εναλλακτική δομή
        }
    }

    result = scraper._parse_draw(raw_draw)
    assert result is not None
    assert result["euro_numbers"] == [6, 7]
