-- ─────────────────────────────────────────────────────────────
-- STAGING TABLES
-- Raw API responses land here. JSONB preserves the full payload
-- so we can re-process historical data if transformation logic
-- changes — a real-world data engineering pattern.
-- ─────────────────────────────────────────────────────────────

-- ─── Weather (Open-Meteo) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS staging.weather_raw (
    id              BIGSERIAL PRIMARY KEY,
    city_name       TEXT NOT NULL,
    country_code    TEXT NOT NULL,
    latitude        NUMERIC(8, 5) NOT NULL,
    longitude       NUMERIC(8, 5) NOT NULL,
    observed_at     TIMESTAMPTZ NOT NULL,
    raw_payload     JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weather_raw_observed_at
    ON staging.weather_raw (observed_at);
CREATE INDEX IF NOT EXISTS idx_weather_raw_city
    ON staging.weather_raw (city_name, country_code);

-- ─── Cryptocurrency (CoinGecko) ────────────────────────────
CREATE TABLE IF NOT EXISTS staging.crypto_raw (
    id              BIGSERIAL PRIMARY KEY,
    coin_id         TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    name            TEXT NOT NULL,
    snapshot_at     TIMESTAMPTZ NOT NULL,
    raw_payload     JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crypto_raw_snapshot_at
    ON staging.crypto_raw (snapshot_at);
CREATE INDEX IF NOT EXISTS idx_crypto_raw_coin
    ON staging.crypto_raw (coin_id);

-- ─── Countries (REST Countries) ────────────────────────────
CREATE TABLE IF NOT EXISTS staging.countries_raw (
    id              BIGSERIAL PRIMARY KEY,
    country_code    TEXT NOT NULL,
    common_name     TEXT NOT NULL,
    raw_payload     JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_countries_raw_code
    ON staging.countries_raw (country_code);
