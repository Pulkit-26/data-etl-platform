-- ─────────────────────────────────────────────────────────────
-- REPORT: Crypto Volatility Analysis
-- For each coin, compute period-over-period price changes using LAG().
-- Demonstrates: LAG window function, time-series analysis,
--               filtering with QUALIFY-equivalent (Postgres uses WHERE in outer)
-- ─────────────────────────────────────────────────────────────

WITH price_with_lag AS (
    SELECT
        d.name                      AS cryptocurrency,
        UPPER(d.symbol)             AS symbol,
        f.snapshot_at,
        f.price_usd,
        LAG(f.price_usd) OVER (
            PARTITION BY f.crypto_key
            ORDER BY f.snapshot_at
        )                           AS prev_price_usd,
        LAG(f.snapshot_at) OVER (
            PARTITION BY f.crypto_key
            ORDER BY f.snapshot_at
        )                           AS prev_snapshot_at
    FROM warehouse.fact_crypto_price f
    JOIN warehouse.dim_cryptocurrency d ON d.crypto_key = f.crypto_key
)
SELECT
    cryptocurrency,
    symbol,
    snapshot_at,
    price_usd,
    prev_price_usd,
    ROUND(price_usd - prev_price_usd, 4)                         AS abs_change,
    ROUND(
        100.0 * (price_usd - prev_price_usd) / NULLIF(prev_price_usd, 0),
        4
    )                                                            AS pct_change,
    EXTRACT(EPOCH FROM (snapshot_at - prev_snapshot_at)) / 60.0 AS minutes_between
FROM price_with_lag
WHERE prev_price_usd IS NOT NULL          -- skip the first row per coin
ORDER BY cryptocurrency, snapshot_at;
