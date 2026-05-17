"""Smoke test: run each extractor and print a summary.

Run from project root:
    venv/Scripts/python.exe tests/smoke_test_extractors.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make `etl` importable when running this script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.config import load_api_config
from etl.extractors.countries import CountriesExtractor
from etl.extractors.crypto import CryptoExtractor
from etl.extractors.weather import WeatherExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def main() -> None:
    api_cfg = load_api_config()

    print("\n=== Weather Extractor ===")
    weather = WeatherExtractor(base_url=api_cfg.open_meteo_url)
    weather_records = weather.extract()
    print(f"Got {len(weather_records)} weather records")
    if weather_records:
        sample = weather_records[0]
        print(f"Sample: {sample['city_name']} ({sample['country_code']})")
        print(f"  observed_at: {sample['observed_at']}")
        print(f"  payload keys: {list(sample['raw_payload'].keys())}")
        daily = sample["raw_payload"].get("daily", {})
        print(f"  daily fields: {list(daily.keys())}")

    print("\n=== Crypto Extractor ===")
    crypto = CryptoExtractor(base_url=api_cfg.coingecko_url)
    crypto_records = crypto.extract()
    print(f"Got {len(crypto_records)} crypto records")
    if crypto_records:
        sample = crypto_records[0]
        print(f"Sample: {sample['name']} ({sample['symbol'].upper()})")
        payload = sample["raw_payload"]
        print(f"  price_usd: ${payload.get('current_price')}")
        print(f"  market_cap: ${payload.get('market_cap'):,}")
        print(f"  24h change: {payload.get('price_change_percentage_24h')}%")

    print("\n=== Countries Extractor ===")
    countries = CountriesExtractor(base_url=api_cfg.rest_countries_url)
    country_records = countries.extract()
    print(f"Got {len(country_records)} country records")
    if country_records:
        sample = next(
            (r for r in country_records if r["country_code"] == "US"),
            country_records[0],
        )
        payload = sample["raw_payload"]
        print(f"Sample: {sample['common_name']} ({sample['country_code']})")
        print(f"  region: {payload.get('region')} / {payload.get('subregion')}")
        print(f"  population: {payload.get('population'):,}")
        print(f"  capital: {payload.get('capital')}")

    print("\nAll extractors ran successfully.")


if __name__ == "__main__":
    main()
