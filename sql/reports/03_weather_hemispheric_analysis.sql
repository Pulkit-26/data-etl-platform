-- ─────────────────────────────────────────────────────────────
-- REPORT: Hemispheric Weather Analysis
-- Compare current temperatures across hemispheres and regions.
-- Demonstrates: CASE classification, GROUP BY ROLLUP, multi-dim joins
-- ─────────────────────────────────────────────────────────────

-- Latest weather observation per city, classified by hemisphere/region.
WITH latest_weather AS (
    SELECT DISTINCT ON (f.location_key)
        f.location_key,
        f.date_key,
        f.temp_max_celsius,
        f.temp_min_celsius,
        f.temp_mean_celsius,
        f.precipitation_mm,
        f.wind_speed_max_kmh
    FROM warehouse.fact_weather_daily f
    ORDER BY f.location_key, f.date_key DESC
),
enriched AS (
    SELECT
        loc.city_name,
        c.country_name,
        c.region,
        CASE
            WHEN loc.latitude >= 23.5  THEN 'Northern temperate/polar'
            WHEN loc.latitude >  -23.5 THEN 'Tropical'
            ELSE                            'Southern temperate/polar'
        END                                 AS climate_zone,
        CASE
            WHEN loc.latitude >= 0 THEN 'Northern'
            ELSE                        'Southern'
        END                                 AS hemisphere,
        w.temp_max_celsius,
        w.temp_min_celsius,
        w.temp_mean_celsius,
        w.precipitation_mm,
        w.wind_speed_max_kmh
    FROM latest_weather w
    JOIN warehouse.dim_location loc ON loc.location_key = w.location_key
    JOIN warehouse.dim_country  c   ON c.country_key   = loc.country_key
)
-- Aggregate by hemisphere AND total (ROLLUP creates subtotals + grand total).
SELECT
    COALESCE(hemisphere, 'ALL HEMISPHERES')          AS hemisphere,
    COUNT(*)                                          AS city_count,
    ROUND(AVG(temp_max_celsius)::NUMERIC, 1)          AS avg_max_c,
    ROUND(AVG(temp_min_celsius)::NUMERIC, 1)          AS avg_min_c,
    ROUND(AVG(temp_mean_celsius)::NUMERIC, 1)         AS avg_mean_c,
    ROUND(SUM(precipitation_mm)::NUMERIC, 1)          AS total_precip_mm,
    MAX(temp_max_celsius)                             AS hottest_max,
    MIN(temp_min_celsius)                             AS coldest_min
FROM enriched
GROUP BY ROLLUP (hemisphere)
ORDER BY hemisphere NULLS LAST;
