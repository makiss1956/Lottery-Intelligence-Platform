"""Unit tests for the OPAPFetcher module."""

from unittest.mock import MagicMock, patch
import pytest
from src.fetchers.opap_fetcher import OPAPFetcher


@pytest.fixture
def opap_fetcher():
    """Fixture to provide a clean OPAPFetcher instance."""
    return OPAPFetcher(timeout=5)


@pytest.fixture
def mock_opap_api_response():
    """Mock JSON response mimicking the OPAP Eurojackpot API format."""
    return [
        {
            "drawId": 12345,
            "drawTime": 1776283200000,  # Example UNIX timestamp in milliseconds
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


def test_fetch_latest_draws_success(opap_fetcher, mock_opap_api_response):
    """Test successful fetching and parsing of draw data."""
    with patch("requests.get") as mock_get:
        # Configuration of the mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_opap_api_response
        mock_get.return_value = mock_response

        # Execute fetcher
        draws = opap_fetcher.fetch_latest_draws(limit=1)

        # Assertions
        mock_get.assert_called_once_with(
            "https://api.opap.gr/draws/v3.0/5104/last/1",
            timeout=5
        )
        assert len(draws) == 1
        assert draws[0]["primary_numbers"] == [5, 12, 18, 33, 45]
        assert draws[0]["euro_numbers"] == [3, 9]
        assert "draw_date" in draws[0]


def test_fetch_latest_draws_http_error(opap_fetcher):
    """Test behavior when API request fails (e.g. 500 Internal Server Error)."""
    with patch("requests.get") as mock_get:
        # Configure mock to raise an HTTP exception
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Server Error")
        mock_get.return_value = mock_response

        # Execute fetcher
        draws = opap_fetcher.fetch_latest_draws(limit=5)

        # Should handle exception gracefully and return an empty list
        assert draws == []


def test_parse_draw_malformed_data(opap_fetcher):
    """Test parsing logic when response contains missing or malformed numbers."""
    malformed_json = [
        {
            "drawId": 99999,
            "drawTime": 1776283200000,
            "winningNumbers": {
                "list": [1, 2],  # Incomplete primary numbers (needs 5)
                "sideLists": {"1": {"list": [3]}}
            }
        }
    ]

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = malformed_json
        mock_get.return_value = mock_response

        draws = opap_fetcher.fetch_latest_draws(limit=1)

        # Malformed entries should be filtered out
        assert draws == []
