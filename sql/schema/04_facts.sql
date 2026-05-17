-- ─────────────────────────────────────────────────────────────
-- FACT TABLES
-- The measurements/events we want to analyze. Each row is a
-- single observation linked to its dimensions via foreign keys.
-- ─────────────────────────────────────────────────────────────

-- ─── fact_weather_daily ────────────────────────────────────
-- One row per location per day. Grain (level of detail) matters:
-- we deliberately aggregate to daily to keep volume manageable
-- while still enabling trend analysis.
CREATE TABLE IF NOT EXISTS warehouse.fact_weather_daily (
    weather_fact_key    BIGSERIAL PRIMARY KEY,
    date_key            INTEGER NOT NULL REFERENCES warehouse.dim_date(date_key),
    location_key        INTEGER NOT NULL REFERENCES warehouse.dim_location(location_key),
    temp_max_celsius    NUMERIC(5, 2),
    temp_min_celsius    NUMERIC(5, 2),
    temp_mean_celsius   NUMERIC(5, 2),
    precipitation_mm    NUMERIC(6, 2),
    wind_speed_max_kmh  NUMERIC(6, 2),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (date_key, location_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_weather_date
    ON warehouse.fact_weather_daily (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_weather_location
    ON warehouse.fact_weather_daily (location_key);

-- ─── fact_crypto_price ─────────────────────────────────────
-- One row per coin per snapshot. Crypto prices move constantly,
-- so we keep a higher grain (each API poll = one row).
CREATE TABLE IF NOT EXISTS warehouse.fact_crypto_price (
    crypto_fact_key     BIGSERIAL PRIMARY KEY,
    date_key            INTEGER NOT NULL REFERENCES warehouse.dim_date(date_key),
    crypto_key          INTEGER NOT NULL REFERENCES warehouse.dim_cryptocurrency(crypto_key),
    snapshot_at         TIMESTAMPTZ NOT NULL,
    price_usd           NUMERIC(20, 8) NOT NULL,
    market_cap_usd      NUMERIC(24, 2),
    total_volume_usd    NUMERIC(24, 2),
    price_change_24h    NUMERIC(10, 4),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (crypto_key, snapshot_at)
);

CREATE INDEX IF NOT EXISTS idx_fact_crypto_date
    ON warehouse.fact_crypto_price (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_crypto_coin
    ON warehouse.fact_crypto_price (crypto_key);
CREATE INDEX IF NOT EXISTS idx_fact_crypto_snapshot
    ON warehouse.fact_crypto_price (snapshot_at);
