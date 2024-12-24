from typing import List

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.parsers.imotinet import ImotiNetParser

logger = get_logger(__file__)


class ImotiNetScraper:
    def __init__(
        self,
        url: str,
        encoding: str = "utf-8",
        headers: dict = None,
        timeout: int = 10,
    ):
        self.url = url
        self.encoding = encoding
        self.http_client = HttpClient(headers=headers, timeout=timeout)
        self.parser = ImotiNetParser()
        self.total_pages = -1

    def fetch_page(self, url: str) -> str:
        try:
            return self.http_client.fetch(url, encoding=self.encoding)
        except Exception:
            logger.error(f"Failed to fetch page {url}")
            raise

    def process(self) -> List[dict]:
        html_content = self.fetch_page(self.url)

        if self.total_pages == -1:
            self.total_pages = self.parser.get_total_pages(html_content)

        results = []
        for page_num in range(1, self.total_pages + 1):
            page_url = self.url.replace("page=1", f"page={page_num}")
            print(page_url)
            html_content = self.fetch_page(page_url)
            logger.info(f"Processing {page_url} (page {page_num} of {self.total_pages})")
            results.extend(self.parser.parse_listings(html_content))

        return results
