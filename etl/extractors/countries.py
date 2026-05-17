"""REST Countries reference data extractor.

Pulls reference data (population, area, region, capital, currency) for
all countries. This is slowly-changing reference data — we only need to
refresh it occasionally, not hourly like weather or crypto.

Docs: https://restcountries.com/
"""

from __future__ import annotations

import logging
from typing import Any

from etl.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


# Restrict fields to reduce payload size — we only need what we'll store.
COUNTRY_FIELDS: tuple[str, ...] = (
    "name",
    "cca2",
    "region",
    "subregion",
    "capital",
    "population",
    "area",
    "currencies",
    "languages",
)


class CountriesExtractor(BaseExtractor):
    """Extracts reference data for all countries."""

    def __init__(self, base_url: str, fields: tuple[str, ...] = COUNTRY_FIELDS) -> None:
        super().__init__(base_url=base_url)
        self.fields = fields

    def extract(self) -> list[dict[str, Any]]:
        params = {"fields": ",".join(self.fields)}
        payload = self._get("all", params=params)

        if not isinstance(payload, list):
            logger.error("Unexpected REST Countries response shape: %s", type(payload))
            return []

        records: list[dict[str, Any]] = []
        for item in payload:
            cca2 = item.get("cca2")
            common_name = item.get("name", {}).get("common")
            if not cca2 or not common_name:
                logger.warning("Skipping country with missing identifiers: %s", item)
                continue
            records.append(
                {
                    "country_code": cca2,
                    "common_name": common_name,
                    "raw_payload": item,
                }
            )

        logger.info("Extracted %d countries", len(records))
        return records
