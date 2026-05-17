"""Transform staging.countries_raw -> warehouse.dim_country.

Uses an INSERT ... SELECT pattern with JSONB extraction to flatten the
nested API payload into our flat dimension table. ON CONFLICT performs
an upsert so re-runs are idempotent.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from etl.loaders.staging import get_engine

logger = logging.getLogger(__name__)


TRANSFORM_SQL = text("""
    INSERT INTO warehouse.dim_country (
        country_code, country_name, region, subregion, capital,
        population, area_km2, currency_code, currency_name, updated_at
    )
    SELECT DISTINCT ON (s.country_code)
        s.country_code,
        s.raw_payload->'name'->>'common'                      AS country_name,
        s.raw_payload->>'region'                              AS region,
        s.raw_payload->>'subregion'                           AS subregion,
        (s.raw_payload->'capital'->>0)                        AS capital,
        NULLIF(s.raw_payload->>'population', '')::BIGINT      AS population,
        NULLIF(s.raw_payload->>'area', '')::NUMERIC(12, 2)    AS area_km2,
        (SELECT key
           FROM jsonb_object_keys(s.raw_payload->'currencies') AS key
           LIMIT 1)                                           AS currency_code,
        (SELECT value->>'name'
           FROM jsonb_each(s.raw_payload->'currencies') AS each(key, value)
           LIMIT 1)                                           AS currency_name,
        NOW()                                                 AS updated_at
    FROM staging.countries_raw s
    WHERE s.raw_payload ? 'name'
    ORDER BY s.country_code, s.ingested_at DESC
    ON CONFLICT (country_code) DO UPDATE SET
        country_name  = EXCLUDED.country_name,
        region        = EXCLUDED.region,
        subregion     = EXCLUDED.subregion,
        capital       = EXCLUDED.capital,
        population    = EXCLUDED.population,
        area_km2      = EXCLUDED.area_km2,
        currency_code = EXCLUDED.currency_code,
        currency_name = EXCLUDED.currency_name,
        updated_at    = NOW();
""")


def transform_countries() -> int:
    """Run the staging->dim_country transformation. Returns rows affected."""
    with get_engine().begin() as conn:
        result = conn.execute(TRANSFORM_SQL)
        rowcount = result.rowcount
    logger.info("Upserted %d rows into warehouse.dim_country", rowcount)
    return rowcount
