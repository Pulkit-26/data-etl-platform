-- ─────────────────────────────────────────────────────────────
-- REPORT: Crypto Market Dashboard
-- Latest market snapshot with ranking, market share, and 24h movement.
-- Demonstrates: window functions (RANK, SUM OVER), CTE, JOINs
-- ─────────────────────────────────────────────────────────────

-- Create as a view so BI tools can read it like a table.
CREATE OR REPLACE VIEW reports.v_crypto_market_dashboard AS
WITH latest_snapshot AS (
    -- For each coin, keep only the most recent fact row.
    SELECT DISTINCT ON (crypto_key)
        crypto_key,
        snapshot_at,
        price_usd,
        market_cap_usd,
        total_volume_usd,
        price_change_24h
    FROM warehouse.fact_crypto_price
    ORDER BY crypto_key, snapshot_at DESC
)
SELECT
    d.name                              AS cryptocurrency,
    UPPER(d.symbol)                     AS symbol,
    l.price_usd,
    l.market_cap_usd,
    l.total_volume_usd,
    l.price_change_24h                  AS pct_change_24h,
    RANK() OVER (ORDER BY l.market_cap_usd DESC NULLS LAST)
                                        AS market_cap_rank,
    ROUND(
        100.0 * l.market_cap_usd
              / SUM(l.market_cap_usd) OVER (),
        4
    )                                   AS market_share_pct,
    CASE
        WHEN l.price_change_24h >  2  THEN 'Strong gain'
        WHEN l.price_change_24h >  0  THEN 'Slight gain'
        WHEN l.price_change_24h >= -2 THEN 'Slight loss'
        ELSE                               'Strong loss'
    END                                 AS movement_category,
    l.snapshot_at                       AS as_of
FROM latest_snapshot l
JOIN warehouse.dim_cryptocurrency d ON d.crypto_key = l.crypto_key;

-- Run the view:
-- SELECT * FROM reports.v_crypto_market_dashboard ORDER BY market_cap_rank;
