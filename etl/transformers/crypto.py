"""Transform staging.crypto_raw -> warehouse dimension + fact tables.

Two-step transformation:
  1. Upsert dim_cryptocurrency (reference data)
  2. Insert into fact_crypto_price (new snapshots)
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from etl.loaders.staging import get_engine

logger = logging.getLogger(__name__)


UPSERT_DIM_SQL = text("""
    INSERT INTO warehouse.dim_cryptocurrency (coin_id, symbol, name, updated_at)
    SELECT DISTINCT ON (s.coin_id)
        s.coin_id,
        s.symbol,
        s.name,
        NOW() AS updated_at
    FROM staging.crypto_raw s
    ORDER BY s.coin_id, s.ingested_at DESC
    ON CONFLICT (coin_id) DO UPDATE SET
        symbol     = EXCLUDED.symbol,
        name       = EXCLUDED.name,
        updated_at = NOW();
""")


INSERT_FACT_SQL = text("""
    INSERT INTO warehouse.fact_crypto_price (
        date_key, crypto_key, snapshot_at,
        price_usd, market_cap_usd, total_volume_usd, price_change_24h
    )
    SELECT
        TO_CHAR(s.snapshot_at, 'YYYYMMDD')::INTEGER          AS date_key,
        d.crypto_key,
        s.snapshot_at,
        (s.raw_payload->>'current_price')::NUMERIC(20, 8)    AS price_usd,
        NULLIF(s.raw_payload->>'market_cap', '')::NUMERIC(24, 2)        AS market_cap_usd,
        NULLIF(s.raw_payload->>'total_volume', '')::NUMERIC(24, 2)      AS total_volume_usd,
        NULLIF(s.raw_payload->>'price_change_percentage_24h', '')::NUMERIC(10, 4) AS price_change_24h
    FROM staging.crypto_raw s
    JOIN warehouse.dim_cryptocurrency d ON d.coin_id = s.coin_id
    WHERE s.raw_payload ? 'current_price'
    ON CONFLICT (crypto_key, snapshot_at) DO NOTHING;
""")


def transform_crypto() -> dict[str, int]:
    """Run dim + fact transformations. Returns rowcounts per table."""
    with get_engine().begin() as conn:
        dim_result = conn.execute(UPSERT_DIM_SQL)
        fact_result = conn.execute(INSERT_FACT_SQL)
    counts = {
        "dim_cryptocurrency": dim_result.rowcount,
        "fact_crypto_price": fact_result.rowcount,
    }
    logger.info("Crypto transform: %s", counts)
    return counts
