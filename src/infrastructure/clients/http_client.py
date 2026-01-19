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

    def _handle_retry(self, url: str, error: Exception, attempt: int) -> None:
        is_last_attempt = attempt >= self.max_retries - 1
        error_type = "Timeout" if isinstance(error, httpx.TimeoutException) else "Request error"

        if is_last_attempt:
            logger.error(f"{error_type} fetching {url} after {self.max_retries} attempts: {error}", exc_info=True)
            return

        wait_time = self.retry_delay * (attempt + 1)
        logger.warning(
            f"{error_type} fetching {url} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s..."
        )
        time.sleep(wait_time)

    def _request_with_retry(self, url: str, parse_response):
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

            except (httpx.TimeoutException, httpx.RequestError) as e:
                last_exception = e
                self._handle_retry(url, e, attempt)

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
