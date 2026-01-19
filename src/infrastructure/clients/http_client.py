import time
from typing import Optional

import httpx

from src.logger_setup import get_logger

logger = get_logger(__name__)


class HttpClient:
    def __init__(
        self,
        headers: Optional[dict] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.headers = headers
        self.timeout = httpx.Timeout(timeout, connect=15.0)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _request_with_retry(self, url: str, parse_response):
        """Execute request with retry logic for timeouts and transient errors."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(
                    headers=self.headers,
                    timeout=self.timeout,
                    transport=httpx.HTTPTransport(retries=2),
                    follow_redirects=True,
                ) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    return parse_response(response)

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(
                        f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Timeout fetching {url} after {self.max_retries} attempts", exc_info=True)

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(
                        f"Request error fetching {url} (attempt {attempt + 1}/{self.max_retries}): {e}, "
                        f"retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request error fetching {url} after {self.max_retries} attempts: {e}", exc_info=True)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching {url}: {e}", exc_info=True)
                raise

        raise last_exception

    def fetch(
        self,
        url: str,
        encoding: str,
    ) -> str:
        def parse_response(response):
            response.encoding = encoding
            return response.text

        return self._request_with_retry(url, parse_response)

    def fetch_json(
        self,
        url: str,
    ) -> dict:
        return self._request_with_retry(url, lambda r: r.json())
