-- ─────────────────────────────────────────────────────────────
-- DIMENSION TABLES
-- Descriptive context for our facts. Each row uniquely identifies
-- a "thing" (a date, a location, a country, a coin) that facts
-- can reference via foreign keys.
-- ─────────────────────────────────────────────────────────────

-- ─── dim_date ──────────────────────────────────────────────
-- Pre-built date dimension. Critical for time-series analysis:
-- enables "group by quarter", "weekday vs weekend", etc.
-- without complex date arithmetic in every query.
CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key        INTEGER PRIMARY KEY,     -- YYYYMMDD format (e.g. 20260517)
    full_date       DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    month_name      TEXT NOT NULL,
    day             SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL,       -- 0 = Sunday
    day_name        TEXT NOT NULL,
    week_of_year    SMALLINT NOT NULL,
    is_weekend      BOOLEAN NOT NULL
);

-- ─── dim_country ───────────────────────────────────────────
-- Reference data from REST Countries API.
CREATE TABLE IF NOT EXISTS warehouse.dim_country (
    country_key     SERIAL PRIMARY KEY,
    country_code    CHAR(2) NOT NULL UNIQUE,  -- ISO 3166-1 alpha-2
    country_name    TEXT NOT NULL,
    region          TEXT,
    subregion       TEXT,
    capital         TEXT,
    population      BIGINT,
    area_km2        NUMERIC(12, 2),
    currency_code   TEXT,
    currency_name   TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── dim_location ──────────────────────────────────────────
-- Cities where we collect weather data. Linked to dim_country.
CREATE TABLE IF NOT EXISTS warehouse.dim_location (
    location_key    SERIAL PRIMARY KEY,
    city_name       TEXT NOT NULL,
    country_key     INTEGER NOT NULL REFERENCES warehouse.dim_country(country_key),
    latitude        NUMERIC(8, 5) NOT NULL,
    longitude       NUMERIC(8, 5) NOT NULL,
    timezone        TEXT,
    UNIQUE (city_name, country_key)
);

-- ─── dim_cryptocurrency ────────────────────────────────────
-- Cryptocurrency reference data.
CREATE TABLE IF NOT EXISTS warehouse.dim_cryptocurrency (
    crypto_key      SERIAL PRIMARY KEY,
    coin_id         TEXT NOT NULL UNIQUE,    -- CoinGecko's id (e.g. "bitcoin")
    symbol          TEXT NOT NULL,           -- e.g. "btc"
    name            TEXT NOT NULL,           -- e.g. "Bitcoin"
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Populate dim_date for a reasonable range (2020-01-01 to 2030-12-31)
-- This is generated once; date dimensions are static reference data.
-- ─────────────────────────────────────────────────────────────
INSERT INTO warehouse.dim_date (
    date_key, full_date, year, quarter, month, month_name,
    day, day_of_week, day_name, week_of_year, is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS date_key,
    d::DATE AS full_date,
    EXTRACT(YEAR FROM d)::SMALLINT AS year,
    EXTRACT(QUARTER FROM d)::SMALLINT AS quarter,
    EXTRACT(MONTH FROM d)::SMALLINT AS month,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(DAY FROM d)::SMALLINT AS day,
    EXTRACT(DOW FROM d)::SMALLINT AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    EXTRACT(WEEK FROM d)::SMALLINT AS week_of_year,
    EXTRACT(DOW FROM d) IN (0, 6) AS is_weekend
FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS d
ON CONFLICT (date_key) DO NOTHING;
