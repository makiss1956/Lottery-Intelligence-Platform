"""Tests for the Eurojackpot OPAP scraper."""

from unittest.mock import MagicMock, patch

from src.importers.web_scraper import EurojackpotWebScraper


def test_fetch_latest_draw_success():
    """Latest draw is parsed correctly from OPAP response."""

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

        draw = scraper.fetch_latest_draw()

    assert draw is not None

    assert draw["primary_numbers"] == [
        5,
        12,
        18,
        33,
        45,
    ]

    assert draw["euro_numbers"] == [
        3,
        9,
    ]

    assert "draw_date" in draw


def test_invalid_draw_is_rejected():
    """Malformed draws must not enter the system."""

    scraper = EurojackpotWebScraper()

    malformed_draw = {
        "drawId": 99999,
        "drawTime": 1776283200000,
        "winningNumbers": {
            "list": [1, 2],
            "sideLists": {
                "1": {
                    "list": [3]
                }
            }
        }
    }

    result = scraper._parse_draw(
        malformed_draw
    )

    assert result is None


def test_valid_draw_parser():
    """Valid OPAP draw is normalized correctly."""

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

    result = scraper._parse_draw(
        raw_draw
    )

    assert result is not None

    assert result["primary_numbers"] == [
        5,
        12,
        18,
        33,
        45,
    ]

    assert result["euro_numbers"] == [
        3,
        9,
    ]
