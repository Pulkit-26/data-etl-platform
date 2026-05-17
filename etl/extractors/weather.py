"""Open-Meteo weather extractor.

Pulls daily weather forecasts (temp, precipitation, wind) for a curated
set of major world cities. Open-Meteo is free and requires no API key.

Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from etl.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class City:
    name: str
    country_code: str  # ISO 3166-1 alpha-2
    latitude: float
    longitude: float
    timezone: str


# Curated list — geographically diverse cities for interesting analytics.
DEFAULT_CITIES: tuple[City, ...] = (
    City("Austin", "US", 30.2672, -97.7431, "America/Chicago"),
    City("New York", "US", 40.7128, -74.0060, "America/New_York"),
    City("London", "GB", 51.5074, -0.1278, "Europe/London"),
    City("Tokyo", "JP", 35.6762, 139.6503, "Asia/Tokyo"),
    City("Sydney", "AU", -33.8688, 151.2093, "Australia/Sydney"),
    City("Mumbai", "IN", 19.0760, 72.8777, "Asia/Kolkata"),
    City("São Paulo", "BR", -23.5505, -46.6333, "America/Sao_Paulo"),
    City("Cape Town", "ZA", -33.9249, 18.4241, "Africa/Johannesburg"),
)


class WeatherExtractor(BaseExtractor):
    """Extracts daily weather data for a list of cities."""

    def __init__(
        self,
        base_url: str,
        cities: tuple[City, ...] = DEFAULT_CITIES,
        forecast_days: int = 1,
    ) -> None:
        super().__init__(base_url=base_url)
        self.cities = cities
        self.forecast_days = forecast_days

    def extract(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        observed_at = datetime.now(UTC)

        for city in self.cities:
            try:
                payload = self._fetch_city(city)
                records.append(
                    {
                        "city_name": city.name,
                        "country_code": city.country_code,
                        "latitude": city.latitude,
                        "longitude": city.longitude,
                        "observed_at": observed_at,
                        "raw_payload": payload,
                    }
                )
            except Exception:
                # Log and continue — one bad city shouldn't kill the whole batch
                logger.exception("Failed to extract weather for %s", city.name)

        logger.info("Extracted weather for %d/%d cities", len(records), len(self.cities))
        return records

    def _fetch_city(self, city: City) -> dict[str, Any]:
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "temperature_2m_mean",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                ]
            ),
            "timezone": city.timezone,
            "forecast_days": self.forecast_days,
        }
        return self._get("", params=params)
