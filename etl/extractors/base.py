"""Abstract base class for all API extractors.

Provides shared HTTP client behavior: timeouts, retries with exponential
backoff, structured logging. Concrete extractors implement extract().
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for API extractors.

    Subclasses must implement extract() which returns a list of dicts
    suitable for loading into the staging layer.
    """

    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 1.5

    def __init__(
        self,
        base_url: str,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = self._build_session(max_retries)

    @staticmethod
    def _build_session(max_retries: int) -> requests.Session:
        """Build a requests session with automatic retry on transient failures."""
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=BaseExtractor.DEFAULT_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "data-etl-platform/1.0 (educational project)",
            }
        )
        return session

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform an authenticated GET and return parsed JSON.

        Raises requests.HTTPError on non-2xx after retries are exhausted.
        """
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        logger.info("GET %s params=%s", url, params)
        start = time.monotonic()
        response = self.session.get(url, params=params, timeout=self.timeout)
        elapsed = time.monotonic() - start
        logger.info("→ %d in %.2fs", response.status_code, elapsed)
        response.raise_for_status()
        return response.json()

    @abstractmethod
    def extract(self) -> list[dict[str, Any]]:
        """Pull data from the source and return a list of records.

        Each record should be a dict with all fields needed to load into
        the corresponding staging table.
        """
        raise NotImplementedError
