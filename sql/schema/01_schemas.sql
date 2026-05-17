-- ─────────────────────────────────────────────────────────────
-- Create namespaces (schemas) for separation of concerns
-- ─────────────────────────────────────────────────────────────
-- staging   : raw data landed from APIs, untransformed
-- warehouse : cleaned, modeled data ready for analytics
-- reports   : views and materialized views for BI tools
-- ─────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;
CREATE SCHEMA IF NOT EXISTS reports;

COMMENT ON SCHEMA staging IS 'Raw landing zone for data extracted from external APIs';
COMMENT ON SCHEMA warehouse IS 'Cleaned, dimensional model (star schema) for analytics';
COMMENT ON SCHEMA reports IS 'Views and aggregations consumed by BI tools and dashboards';
