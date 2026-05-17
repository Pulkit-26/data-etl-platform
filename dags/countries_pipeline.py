"""Countries reference data pipeline DAG.

Slow-changing reference data refreshed weekly. Other pipelines (weather)
depend on warehouse.dim_country being populated, so this DAG should run
first after initial deployment.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from etl.config import load_api_config
from etl.extractors.countries import CountriesExtractor
from etl.loaders.staging import load_countries_staging
from etl.transformers.countries import transform_countries

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


@dag(
    dag_id="countries_pipeline",
    description="Weekly refresh of country reference data",
    start_date=datetime(2026, 1, 1),
    schedule="@weekly",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["etl", "reference", "weekly"],
    doc_md=__doc__,
)
def countries_pipeline():

    @task(task_id="extract_and_load_staging")
    def extract_and_load() -> int:
        api_cfg = load_api_config()
        extractor = CountriesExtractor(base_url=api_cfg.rest_countries_url)
        records = extractor.extract()
        return load_countries_staging(records)

    @task(task_id="transform_to_warehouse")
    def transform(rows_loaded: int) -> int:
        return transform_countries()

    rows = extract_and_load()
    transform(rows)


dag_instance = countries_pipeline()
