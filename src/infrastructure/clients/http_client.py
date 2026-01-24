import time
from typing import Callable, TypeVar

import httpx

from src.infrastructure.clients.browser_profiles import get_random_profile
from src.logger_setup import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class HttpClient:
    """
    HTTP client with browser-like headers and retry logic.

    On initialization, selects a random browser profile (User-Agent, Sec-CH-UA, etc.)
    to simulate a real browser. The same profile is used for all requests made by
    this client instance (per-session rotation).

    Retries on:
    - Network errors (timeouts, connection failures)
    - Server errors (5xx status codes)
    """

    def __init__(
        self,
        headers: dict | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        browser_profile = get_random_profile()
        self.headers = {**browser_profile, **(headers or {})}
        logger.debug(f"Using browser profile: {self.headers.get('User-Agent', 'unknown')[:50]}...")
        self.timeout = httpx.Timeout(timeout, connect=15.0)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code in RETRYABLE_STATUS_CODES

    def _handle_retry(self, url: str, error: Exception, attempt: int) -> None:
        is_last_attempt = attempt >= self.max_retries - 1

        if isinstance(error, httpx.TimeoutException):
            error_type = "Timeout"
        elif isinstance(error, httpx.HTTPStatusError):
            error_type = f"HTTP {error.response.status_code}"
        else:
            error_type = "Request error"

        if is_last_attempt:
            logger.error(f"{error_type} fetching {url} after {self.max_retries} attempts: {error}", exc_info=True)
            return

        wait_time = self.retry_delay * (attempt + 1)
        logger.warning(
            f"{error_type} fetching {url} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s..."
        )
        time.sleep(wait_time)

    def _request_with_retry(self, url: str, parse_response: Callable[[httpx.Response], T]) -> T:
        last_exception: Exception | None = None

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
                if self._is_retryable_status(e.response.status_code):
                    last_exception = e
                    self._handle_retry(url, e, attempt)
                else:
                    logger.error(f"HTTP error fetching {url}: {e}")
                    raise

        if last_exception:
            raise last_exception
        raise RuntimeError(f"Unexpected state: no response and no exception for {url}")

    def fetch(self, url: str, encoding: str) -> str:
        def parse_response(response: httpx.Response) -> str:
            response.encoding = encoding
            return response.text

        return self._request_with_retry(url, parse_response)

    def fetch_json(self, url: str) -> dict:
        return self._request_with_retry(url, lambda r: r.json())
