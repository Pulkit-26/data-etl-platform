"""CoinGecko cryptocurrency market data extractor.

Pulls current market snapshots (price, market cap, volume, 24h change)
for a curated set of major cryptocurrencies. Free tier — no API key needed.

Docs: https://www.coingecko.com/en/api/documentation
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from etl.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


# Top-tier coins by market cap — stable subset for demo purposes.
DEFAULT_COIN_IDS: tuple[str, ...] = (
    "bitcoin",
    "ethereum",
    "binancecoin",
    "solana",
    "cardano",
    "ripple",
    "polkadot",
    "dogecoin",
)


class CryptoExtractor(BaseExtractor):
    """Extracts current market data for a list of cryptocurrencies."""

    def __init__(
        self,
        base_url: str,
        coin_ids: tuple[str, ...] = DEFAULT_COIN_IDS,
        vs_currency: str = "usd",
    ) -> None:
        super().__init__(base_url=base_url)
        self.coin_ids = coin_ids
        self.vs_currency = vs_currency

    def extract(self) -> list[dict[str, Any]]:
        snapshot_at = datetime.now(UTC)
        params = {
            "vs_currency": self.vs_currency,
            "ids": ",".join(self.coin_ids),
            "order": "market_cap_desc",
            "per_page": len(self.coin_ids),
            "page": 1,
            "price_change_percentage": "24h",
        }
        payload = self._get("coins/markets", params=params)

        if not isinstance(payload, list):
            logger.error("Unexpected CoinGecko response shape: %s", type(payload))
            return []

        records = [
            {
                "coin_id": item["id"],
                "symbol": item["symbol"],
                "name": item["name"],
                "snapshot_at": snapshot_at,
                "raw_payload": item,
            }
            for item in payload
        ]
        logger.info("Extracted %d crypto snapshots", len(records))
        return records
