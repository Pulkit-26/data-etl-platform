"""End-to-end smoke test:
  1. Extract from each API
  2. Load raw data into staging tables
  3. Run transformations into warehouse dim/fact tables
  4. Query the warehouse to verify

Run from project root:
    venv/Scripts/python.exe tests/smoke_test_pipeline.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# When running locally (not in Docker), warehouse is on localhost
os.environ.setdefault("WAREHOUSE_HOST", "localhost")

from sqlalchemy import text

from etl.config import load_api_config
from etl.extractors.countries import CountriesExtractor
from etl.extractors.crypto import CryptoExtractor
from etl.extractors.weather import WeatherExtractor
from etl.loaders.staging import (
    get_engine,
    load_countries_staging,
    load_crypto_staging,
    load_weather_staging,
)
from etl.transformers.countries import transform_countries
from etl.transformers.crypto import transform_crypto
from etl.transformers.weather import transform_weather

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("smoke_test")


def main() -> None:
    api_cfg = load_api_config()

    # ── EXTRACT ────────────────────────────────────────────
    logger.info("=== EXTRACT ===")
    weather_records = WeatherExtractor(api_cfg.open_meteo_url).extract()
    crypto_records = CryptoExtractor(api_cfg.coingecko_url).extract()
    countries_records = CountriesExtractor(api_cfg.rest_countries_url).extract()

    # ── LOAD to staging ────────────────────────────────────
    logger.info("=== LOAD STAGING ===")
    load_countries_staging(countries_records)
    load_weather_staging(weather_records)
    load_crypto_staging(crypto_records)

    # ── TRANSFORM ──────────────────────────────────────────
    # Countries first (other dims depend on dim_country)
    logger.info("=== TRANSFORM ===")
    transform_countries()
    transform_weather()
    transform_crypto()

    # ── VERIFY ─────────────────────────────────────────────
    logger.info("=== VERIFY ===")
    with get_engine().connect() as conn:
        for table in [
            "staging.weather_raw",
            "staging.crypto_raw",
            "staging.countries_raw",
            "warehouse.dim_country",
            "warehouse.dim_location",
            "warehouse.dim_cryptocurrency",
            "warehouse.fact_weather_daily",
            "warehouse.fact_crypto_price",
        ]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table:<40} {count:>8} rows")

        print("\n=== Sample: weather facts joined with location + country ===")
        rows = conn.execute(
            text("""
            SELECT
                l.city_name,
                c.country_name,
                d.full_date,
                f.temp_max_celsius,
                f.temp_min_celsius,
                f.precipitation_mm
            FROM warehouse.fact_weather_daily f
            JOIN warehouse.dim_location l ON l.location_key = f.location_key
            JOIN warehouse.dim_country  c ON c.country_key  = l.country_key
            JOIN warehouse.dim_date     d ON d.date_key     = f.date_key
            ORDER BY f.temp_max_celsius DESC
        """)
        ).all()
        for r in rows:
            print(
                f"  {r.city_name:<12} ({r.country_name:<20}) "
                f"{r.full_date}  max {r.temp_max_celsius}°C  "
                f"min {r.temp_min_celsius}°C  precip {r.precipitation_mm}mm"
            )

        print("\n=== Sample: latest crypto prices ===")
        rows = conn.execute(
            text("""
            SELECT
                d.name,
                d.symbol,
                f.price_usd,
                f.market_cap_usd,
                f.price_change_24h
            FROM warehouse.fact_crypto_price f
            JOIN warehouse.dim_cryptocurrency d ON d.crypto_key = f.crypto_key
            ORDER BY f.market_cap_usd DESC
        """)
        ).all()
        for r in rows:
            print(
                f"  {r.name:<14} ({r.symbol.upper():<5}) "
                f"${r.price_usd:>12,.2f}  "
                f"cap ${r.market_cap_usd:>20,.0f}  "
                f"24h {r.price_change_24h}%"
            )

    print("\nPipeline ran end-to-end successfully.")


if __name__ == "__main__":
    main()
