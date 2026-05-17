-- ─────────────────────────────────────────────────────────────
-- REPORT: Country-Weather Enrichment
-- Join weather observations to country reference data to compute
-- population-weighted temperature and other cross-source metrics.
-- Demonstrates: multi-source joins (true value of dimensional modeling),
--               computed metrics, FILTER clause, NTILE bucketing
-- ─────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW reports.v_country_weather_enrichment AS
WITH latest_weather AS (
    SELECT DISTINCT ON (location_key)
        location_key,
        date_key,
        temp_max_celsius,
        temp_min_celsius,
        temp_mean_celsius,
        precipitation_mm
    FROM warehouse.fact_weather_daily
    ORDER BY location_key, date_key DESC
)
SELECT
    c.country_name,
    c.region,
    c.subregion,
    c.population,
    c.area_km2,
    ROUND((c.population / NULLIF(c.area_km2, 0))::NUMERIC, 1) AS pop_density_per_km2,
    loc.city_name                                       AS observed_city,
    w.temp_max_celsius,
    w.temp_mean_celsius,
    w.precipitation_mm,
    -- Bucket countries into population quartiles
    NTILE(4) OVER (ORDER BY c.population)               AS population_quartile,
    -- Quick categorical flags for filterable BI dashboards
    (w.precipitation_mm > 0)                            AS had_rain_today,
    (w.temp_max_celsius >= 30)                          AS hot_day_flag,
    d.full_date                                         AS observation_date
FROM latest_weather w
JOIN warehouse.dim_location loc ON loc.location_key = w.location_key
JOIN warehouse.dim_country  c   ON c.country_key   = loc.country_key
JOIN warehouse.dim_date     d   ON d.date_key     = w.date_key;

-- Example queries to run against the view:
--
-- Sum population covered by current weather observations:
-- SELECT SUM(population) AS population_observed
-- FROM reports.v_country_weather_enrichment;
--
-- Population-weighted average temperature:
-- SELECT
--   ROUND(
--     (SUM(temp_mean_celsius * population) / SUM(population))::NUMERIC,
--     2
--   ) AS pop_weighted_temp_c
-- FROM reports.v_country_weather_enrichment;
--
-- Cities where it's both hot AND raining (interesting outliers):
-- SELECT observed_city, country_name, temp_max_celsius, precipitation_mm
-- FROM reports.v_country_weather_enrichment
-- WHERE hot_day_flag AND had_rain_today;
