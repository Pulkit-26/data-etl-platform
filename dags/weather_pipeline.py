"""Weather pipeline DAG.

Hourly extraction of weather data from Open-Meteo for a curated set of
cities, loaded into the staging layer and transformed into the warehouse
star schema.

Dependencies:
    Requires warehouse.dim_country to be populated (run countries_pipeline
    at least once before this DAG, or country joins will be no-ops).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from etl.config import load_api_config
from etl.extractors.weather import WeatherExtractor
from etl.loaders.staging import load_weather_staging
from etl.transformers.weather import transform_weather

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
    "email_on_failure": False,
}


@dag(
    dag_id="weather_pipeline",
    description="Hourly extract/load/transform of weather data",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["etl", "weather", "hourly"],
    doc_md=__doc__,
)
def weather_pipeline():

    @task(task_id="extract_and_load_staging")
    def extract_and_load() -> int:
        """Pull from Open-Meteo and bulk-insert raw JSON into staging."""
        api_cfg = load_api_config()
        extractor = WeatherExtractor(base_url=api_cfg.open_meteo_url)
        records = extractor.extract()
        return load_weather_staging(records)

    @task(task_id="transform_to_warehouse")
    def transform(rows_loaded: int) -> dict[str, int]:
        """Upsert dim_location and append to fact_weather_daily."""
        return transform_weather()

    rows = extract_and_load()
    transform(rows)


dag_instance = weather_pipeline()
