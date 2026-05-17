"""Unit tests for extractors.

These tests do NOT hit real APIs. We mock the HTTP layer so tests are
fast, deterministic, and runnable in CI without network access.
"""

from __future__ import annotations

from unittest.mock import patch

from etl.extractors.countries import CountriesExtractor
from etl.extractors.crypto import CryptoExtractor
from etl.extractors.weather import City, WeatherExtractor

# ─── WeatherExtractor ──────────────────────────────────────────


def test_weather_extractor_handles_successful_response():
    extractor = WeatherExtractor(
        base_url="https://example.com",
        cities=(City("Test City", "US", 10.0, 20.0, "UTC"),),
    )
    fake_payload = {
        "timezone": "UTC",
        "daily": {
            "time": ["2026-05-17"],
            "temperature_2m_max": [25.5],
            "temperature_2m_min": [18.2],
        },
    }
    with patch.object(extractor, "_get", return_value=fake_payload):
        records = extractor.extract()

    assert len(records) == 1
    record = records[0]
    assert record["city_name"] == "Test City"
    assert record["country_code"] == "US"
    assert record["raw_payload"] == fake_payload


def test_weather_extractor_continues_after_failure():
    """One bad city should not kill the batch."""
    extractor = WeatherExtractor(
        base_url="https://example.com",
        cities=(
            City("Good", "US", 10.0, 20.0, "UTC"),
            City("Bad", "US", 11.0, 21.0, "UTC"),
        ),
    )
    fake_payload = {"daily": {"time": ["2026-05-17"]}}

    call_count = {"n": 0}

    def fake_get(path, params=None):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated API failure")
        return fake_payload

    with patch.object(extractor, "_get", side_effect=fake_get):
        records = extractor.extract()

    assert len(records) == 1
    assert records[0]["city_name"] == "Good"


# ─── CryptoExtractor ───────────────────────────────────────────


def test_crypto_extractor_parses_market_data():
    extractor = CryptoExtractor(
        base_url="https://example.com",
        coin_ids=("bitcoin",),
    )
    fake_response = [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 1_000_000_000,
        }
    ]
    with patch.object(extractor, "_get", return_value=fake_response):
        records = extractor.extract()

    assert len(records) == 1
    assert records[0]["coin_id"] == "bitcoin"
    assert records[0]["symbol"] == "btc"


def test_crypto_extractor_handles_unexpected_response_shape():
    """If API returns a dict instead of a list, return [] gracefully."""
    extractor = CryptoExtractor(base_url="https://example.com")
    with patch.object(extractor, "_get", return_value={"error": "rate limit"}):
        records = extractor.extract()
    assert records == []


# ─── CountriesExtractor ────────────────────────────────────────


def test_countries_extractor_skips_records_with_missing_identifiers():
    extractor = CountriesExtractor(base_url="https://example.com")
    fake_response = [
        {"cca2": "US", "name": {"common": "United States"}},
        {"cca2": "XX"},  # missing name → skip
        {"name": {"common": "Nowhere"}},  # missing cca2 → skip
        {"cca2": "FR", "name": {"common": "France"}},
    ]
    with patch.object(extractor, "_get", return_value=fake_response):
        records = extractor.extract()

    assert len(records) == 2
    codes = {r["country_code"] for r in records}
    assert codes == {"US", "FR"}


# ─── Base behaviour ────────────────────────────────────────────


def test_base_extractor_strips_trailing_slash():
    extractor = CryptoExtractor(base_url="https://api.example.com/")
    assert extractor.base_url == "https://api.example.com"
