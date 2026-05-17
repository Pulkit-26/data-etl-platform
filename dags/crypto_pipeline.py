"""Crypto pipeline DAG.

High-frequency (every 15 minutes) extraction of cryptocurrency market
snapshots from CoinGecko. Each run inserts a new row per coin into
fact_crypto_price, giving us a time-series of price/market_cap/volume.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from etl.config import load_api_config
from etl.extractors.crypto import CryptoExtractor
from etl.loaders.staging import load_crypto_staging
from etl.transformers.crypto import transform_crypto

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


@dag(
    dag_id="crypto_pipeline",
    description="High-frequency extract/load/transform of crypto market data",
    start_date=datetime(2026, 1, 1),
    schedule="*/15 * * * *",  # every 15 minutes
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["etl", "crypto", "high-frequency"],
    doc_md=__doc__,
)
def crypto_pipeline():
    @task(task_id="extract_and_load_staging")
    def extract_and_load() -> int:
        api_cfg = load_api_config()
        extractor = CryptoExtractor(base_url=api_cfg.coingecko_url)
        records = extractor.extract()
        return load_crypto_staging(records)

    @task(task_id="transform_to_warehouse")
    def transform(rows_loaded: int) -> dict[str, int]:
        return transform_crypto()

    rows = extract_and_load()
    transform(rows)


dag_instance = crypto_pipeline()
