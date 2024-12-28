from typing import Optional

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.parsers.imotbg import ImotBg, RawImotBgListingData

logger = get_logger(__file__)


class ImotBgScraper:
    def __init__(
        self,
        url: str,
        encoding: str = "windows-1251",
        headers: Optional[dict] = None,
        timeout: int = 10,
        raw_path_prefix="data/raw/imotbg",
    ):
        self.url = url
        self.encoding = encoding
        self.http_client = HttpClient(
            headers=headers,
            timeout=timeout,
        )

        self.parser = ImotBg()
        self.total_pages = -1
        self.raw_path_prefix = raw_path_prefix

    def fetch_page(self, url: str) -> str:
        try:
            return self.http_client.fetch(
                url=url,
                encoding=self.encoding,
            )
        except Exception:
            logger.error(f"Failed to fetch page {url}")
            raise

    def process(self) -> list[RawImotBgListingData]:
        html_content = self.fetch_page(self.url)
        if self.total_pages == -1:
            self.total_pages = self.parser.get_total_pages(html_content)

        results = []
        for page_num in range(1, self.total_pages + 1):
            page_url = self.url.replace("f1=1", f"f1={page_num}")
            html_content = self.fetch_page(page_url)
            logger.info(f"Processing {page_url} page {page_num} of {self.total_pages}")
            pressed_listings = self.parser.parse_listings(html_content)
            results.extend(pressed_listings)

        return results
