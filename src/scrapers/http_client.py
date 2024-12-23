import httpx
from typing import Optional

from src.logger_setup import get_logger

logger = get_logger(__name__)


class HttpClient:
    def __init__(
        self,
        headers: Optional[dict] = None,
        timeout: int = 10,
    ):
        self.headers = headers
        self.timeout = timeout

    def fetch(
        self,
        url: str,
        encoding: str = "utf-8",
    ) -> str:
        with httpx.Client(
            headers=self.headers,
            timeout=self.timeout,
            transport=httpx.HTTPTransport(retries=5),
        ) as client:
            try:
                response = client.get(url)
                response.encoding = encoding
                response.raise_for_status()
                return response.text
            except httpx.RequestError as e:
                logger.error(f"Error fetching content from {url}: {e}")
                raise
