-- ─────────────────────────────────────────────────────────────
-- REPORT: Data Quality / Pipeline Health
-- Operational query for monitoring the warehouse:
--   - Row counts per table
--   - Freshness (how recent is the latest data?)
--   - Completeness (any expected rows missing?)
--   - Referential integrity (any orphaned facts?)
-- Demonstrates: UNION ALL across heterogeneous results, FILTER clause,
--               LEFT JOIN for orphan detection.
-- ─────────────────────────────────────────────────────────────

-- 1) Row counts and freshness per fact/dimension table
SELECT
    'staging.weather_raw'           AS object,
    (SELECT COUNT(*) FROM staging.weather_raw)::TEXT          AS row_count,
    (SELECT MAX(ingested_at) FROM staging.weather_raw)::TEXT  AS latest_load
UNION ALL SELECT 'staging.crypto_raw',
    (SELECT COUNT(*) FROM staging.crypto_raw)::TEXT,
    (SELECT MAX(ingested_at) FROM staging.crypto_raw)::TEXT
UNION ALL SELECT 'staging.countries_raw',
    (SELECT COUNT(*) FROM staging.countries_raw)::TEXT,
    (SELECT MAX(ingested_at) FROM staging.countries_raw)::TEXT
UNION ALL SELECT 'warehouse.dim_country',
    (SELECT COUNT(*) FROM warehouse.dim_country)::TEXT,
    (SELECT MAX(updated_at) FROM warehouse.dim_country)::TEXT
UNION ALL SELECT 'warehouse.dim_location',
    (SELECT COUNT(*) FROM warehouse.dim_location)::TEXT,
    NULL
UNION ALL SELECT 'warehouse.dim_cryptocurrency',
    (SELECT COUNT(*) FROM warehouse.dim_cryptocurrency)::TEXT,
    (SELECT MAX(updated_at) FROM warehouse.dim_cryptocurrency)::TEXT
UNION ALL SELECT 'warehouse.fact_weather_daily',
    (SELECT COUNT(*) FROM warehouse.fact_weather_daily)::TEXT,
    (SELECT MAX(loaded_at) FROM warehouse.fact_weather_daily)::TEXT
UNION ALL SELECT 'warehouse.fact_crypto_price',
    (SELECT COUNT(*) FROM warehouse.fact_crypto_price)::TEXT,
    (SELECT MAX(loaded_at) FROM warehouse.fact_crypto_price)::TEXT;


-- 2) Freshness check: alert if any fact is older than a freshness SLA
WITH freshness AS (
    SELECT
        'fact_weather_daily' AS table_name,
        MAX(loaded_at)       AS last_loaded,
        '2 hours'::INTERVAL  AS sla
    FROM warehouse.fact_weather_daily
    UNION ALL
    SELECT
        'fact_crypto_price',
        MAX(loaded_at),
        '30 minutes'::INTERVAL
    FROM warehouse.fact_crypto_price
)
SELECT
    table_name,
    last_loaded,
    NOW() - last_loaded                AS age,
    sla,
    CASE
        WHEN NOW() - last_loaded <= sla THEN 'OK'
        ELSE 'STALE'
    END                                AS sla_status
FROM freshness;


-- 3) Per-coin coverage: which coins have N snapshots in the last 24 hours?
SELECT
    d.name                                              AS cryptocurrency,
    COUNT(*) FILTER (WHERE f.snapshot_at >= NOW() - INTERVAL '24 hours')
                                                        AS snapshots_24h,
    COUNT(*)                                            AS snapshots_total,
    MIN(f.snapshot_at)                                  AS first_seen,
    MAX(f.snapshot_at)                                  AS last_seen
FROM warehouse.fact_crypto_price f
JOIN warehouse.dim_cryptocurrency d ON d.crypto_key = f.crypto_key
GROUP BY d.name
ORDER BY snapshots_24h DESC;


-- 4) Orphan check: any locations whose country reference is missing?
SELECT
    loc.location_key,
    loc.city_name,
    loc.country_key
FROM warehouse.dim_location loc
LEFT JOIN warehouse.dim_country c ON c.country_key = loc.country_key
WHERE c.country_key IS NULL;
