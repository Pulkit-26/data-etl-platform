"""Transform staging.weather_raw -> warehouse dimension + fact tables.

Three-step transformation:
  1. Upsert dim_location (city/country/lat/lon/timezone)
  2. Insert into fact_weather_daily by unpacking parallel daily arrays

Open-Meteo returns daily metrics as parallel arrays (daily.time[], temperature_2m_max[], ...)
which we unzip using WITH ORDINALITY to align positions across arrays.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from etl.loaders.staging import get_engine

logger = logging.getLogger(__name__)


UPSERT_DIM_SQL = text("""
    INSERT INTO warehouse.dim_location (
        city_name, country_key, latitude, longitude, timezone
    )
    SELECT DISTINCT ON (s.city_name, c.country_key)
        s.city_name,
        c.country_key,
        s.latitude,
        s.longitude,
        s.raw_payload->>'timezone' AS timezone
    FROM staging.weather_raw s
    JOIN warehouse.dim_country c ON c.country_code = s.country_code
    ORDER BY s.city_name, c.country_key, s.ingested_at DESC
    ON CONFLICT (city_name, country_key) DO UPDATE SET
        latitude  = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        timezone  = EXCLUDED.timezone;
""")


INSERT_FACT_SQL = text("""
    WITH unpacked AS (
        SELECT
            s.id AS staging_id,
            s.city_name,
            s.country_code,
            day_time.value::TEXT::DATE AS observation_date,
            (temp_max.value)::TEXT::NUMERIC(5, 2) AS temp_max,
            (temp_min.value)::TEXT::NUMERIC(5, 2) AS temp_min,
            (temp_mean.value)::TEXT::NUMERIC(5, 2) AS temp_mean,
            (precip.value)::TEXT::NUMERIC(6, 2) AS precipitation,
            (wind.value)::TEXT::NUMERIC(6, 2) AS wind_max
        FROM staging.weather_raw s
        CROSS JOIN LATERAL jsonb_array_elements(s.raw_payload->'daily'->'time')
            WITH ORDINALITY AS day_time(value, idx)
        LEFT JOIN LATERAL jsonb_array_elements(s.raw_payload->'daily'->'temperature_2m_max')
            WITH ORDINALITY AS temp_max(value, idx)   ON temp_max.idx   = day_time.idx
        LEFT JOIN LATERAL jsonb_array_elements(s.raw_payload->'daily'->'temperature_2m_min')
            WITH ORDINALITY AS temp_min(value, idx)   ON temp_min.idx   = day_time.idx
        LEFT JOIN LATERAL jsonb_array_elements(s.raw_payload->'daily'->'temperature_2m_mean')
            WITH ORDINALITY AS temp_mean(value, idx)  ON temp_mean.idx  = day_time.idx
        LEFT JOIN LATERAL jsonb_array_elements(s.raw_payload->'daily'->'precipitation_sum')
            WITH ORDINALITY AS precip(value, idx)     ON precip.idx     = day_time.idx
        LEFT JOIN LATERAL jsonb_array_elements(s.raw_payload->'daily'->'wind_speed_10m_max')
            WITH ORDINALITY AS wind(value, idx)       ON wind.idx       = day_time.idx
    )
    INSERT INTO warehouse.fact_weather_daily (
        date_key, location_key,
        temp_max_celsius, temp_min_celsius, temp_mean_celsius,
        precipitation_mm, wind_speed_max_kmh
    )
    SELECT DISTINCT ON (TO_CHAR(u.observation_date, 'YYYYMMDD')::INTEGER, loc.location_key)
        TO_CHAR(u.observation_date, 'YYYYMMDD')::INTEGER AS date_key,
        loc.location_key,
        u.temp_max,
        u.temp_min,
        u.temp_mean,
        u.precipitation,
        u.wind_max
    FROM unpacked u
    JOIN warehouse.dim_country c   ON c.country_code = u.country_code
    JOIN warehouse.dim_location loc ON loc.city_name = u.city_name
                                   AND loc.country_key = c.country_key
    ON CONFLICT (date_key, location_key) DO UPDATE SET
        temp_max_celsius   = EXCLUDED.temp_max_celsius,
        temp_min_celsius   = EXCLUDED.temp_min_celsius,
        temp_mean_celsius  = EXCLUDED.temp_mean_celsius,
        precipitation_mm   = EXCLUDED.precipitation_mm,
        wind_speed_max_kmh = EXCLUDED.wind_speed_max_kmh,
        loaded_at          = NOW();
""")


def transform_weather() -> dict[str, int]:
    """Run dim + fact transformations. Returns rowcounts per table."""
    with get_engine().begin() as conn:
        dim_result = conn.execute(UPSERT_DIM_SQL)
        fact_result = conn.execute(INSERT_FACT_SQL)
    counts = {
        "dim_location": dim_result.rowcount,
        "fact_weather_daily": fact_result.rowcount,
    }
    logger.info("Weather transform: %s", counts)
    return counts
