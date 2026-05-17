"""Loaders for the staging schema.

Each function takes a list of record dicts (as produced by an extractor)
and bulk-inserts them into the corresponding staging table. Raw payloads
are stored as JSONB so the original API response is preserved.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from etl.config import load_warehouse_config

logger = logging.getLogger(__name__)


_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine (connection pool)."""
    global _engine
    if _engine is None:
        cfg = load_warehouse_config()
        _engine = create_engine(
            cfg.sqlalchemy_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # validate connections before use
        )
    return _engine


def _serialize_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize raw_payload dicts to JSON strings for JSONB columns."""
    serialized = []
    for record in records:
        copy = dict(record)
        if "raw_payload" in copy and not isinstance(copy["raw_payload"], str):
            copy["raw_payload"] = json.dumps(copy["raw_payload"], default=str)
        serialized.append(copy)
    return serialized


def load_weather_staging(records: list[dict[str, Any]]) -> int:
    """Bulk-insert weather records into staging.weather_raw."""
    if not records:
        logger.info("No weather records to load")
        return 0

    sql = text("""
        INSERT INTO staging.weather_raw
            (city_name, country_code, latitude, longitude, observed_at, raw_payload)
        VALUES
            (:city_name, :country_code, :latitude, :longitude, :observed_at,
             CAST(:raw_payload AS JSONB))
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, _serialize_records(records))
    logger.info("Loaded %d rows into staging.weather_raw", len(records))
    return len(records)


def load_crypto_staging(records: list[dict[str, Any]]) -> int:
    """Bulk-insert crypto records into staging.crypto_raw."""
    if not records:
        logger.info("No crypto records to load")
        return 0

    sql = text("""
        INSERT INTO staging.crypto_raw
            (coin_id, symbol, name, snapshot_at, raw_payload)
        VALUES
            (:coin_id, :symbol, :name, :snapshot_at, CAST(:raw_payload AS JSONB))
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, _serialize_records(records))
    logger.info("Loaded %d rows into staging.crypto_raw", len(records))
    return len(records)


def load_countries_staging(records: list[dict[str, Any]]) -> int:
    """Bulk-insert country records into staging.countries_raw."""
    if not records:
        logger.info("No country records to load")
        return 0

    sql = text("""
        INSERT INTO staging.countries_raw
            (country_code, common_name, raw_payload)
        VALUES
            (:country_code, :common_name, CAST(:raw_payload AS JSONB))
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, _serialize_records(records))
    logger.info("Loaded %d rows into staging.countries_raw", len(records))
    return len(records)
