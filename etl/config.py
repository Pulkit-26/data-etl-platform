"""Centralized configuration loaded from environment variables.

All ETL modules import settings from here rather than reading os.environ
directly. This makes the code easier to test, document, and refactor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. Check your .env file."
        )
    return value


@dataclass(frozen=True)
class WarehouseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class ApiConfig:
    open_meteo_url: str
    coingecko_url: str
    rest_countries_url: str


def load_warehouse_config() -> WarehouseConfig:
    return WarehouseConfig(
        host=os.environ.get("WAREHOUSE_HOST", "localhost"),
        port=int(os.environ.get("WAREHOUSE_PORT", "5432")),
        database=_require("POSTGRES_DB")
        if "POSTGRES_DB" in os.environ
        else _require("WAREHOUSE_DB"),
        user=os.environ.get("WAREHOUSE_USER") or _require("POSTGRES_USER"),
        password=os.environ.get("WAREHOUSE_PASSWORD") or _require("POSTGRES_PASSWORD"),
    )


def load_api_config() -> ApiConfig:
    return ApiConfig(
        open_meteo_url=os.environ.get("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast"),
        coingecko_url=os.environ.get("COINGECKO_URL", "https://api.coingecko.com/api/v3"),
        rest_countries_url=os.environ.get("REST_COUNTRIES_URL", "https://restcountries.com/v3.1"),
    )
