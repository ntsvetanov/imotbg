import gzip
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.parser import BaseParser
from src.infrastructure.clients.http_client import CloudscraperHttpClient, HttpClient
from src.logger_setup import get_logger
from src.utils import get_year_month_path, parse_soup

logger = get_logger(__name__)


class Downloader:
    def __init__(self, parser: BaseParser, result_folder: str = "results"):
        self.parser = parser
        self.config = parser.config
        self.result_folder = result_folder
        self.timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        self.http_client = self._create_http_client()

    def _create_http_client(self) -> HttpClient | CloudscraperHttpClient:
        if self.config.use_cloudscraper:
            return CloudscraperHttpClient(timeout=60, max_retries=3, retry_delay=3.0)
        return HttpClient(timeout=60, max_retries=3, retry_delay=3.0)

    def _fetch_with_raw(self, url: str) -> tuple[str, any]:
        if self.config.source_type == "json":
            data = self.http_client.fetch_json(url)
            raw_str = json.dumps(data, ensure_ascii=False, indent=2)
            return raw_str, data

        raw_html = self.http_client.fetch(url, self.config.encoding)
        return raw_html, parse_soup(raw_html)

    def _build_path(self, base: str, folder: str | None) -> Path:
        year_month = get_year_month_path()
        path = Path(self.result_folder) / year_month / base / self.config.name
        if folder:
            path = path / folder
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save_raw_csv(self, listings: list[dict], folder: str | None, url_index: int) -> Path:
        path = self._build_path("raw", folder)
        file_path = path / f"{self.timestamp}_{url_index}.csv"
        pd.DataFrame(listings).to_csv(file_path, index=False, encoding="utf-8")
        logger.info(f"[{self.config.name}] Saved {len(listings)} listings to {file_path}")
        return file_path

    def _save_fallback(self, content: str, folder: str | None, url_index: int) -> Path:
        path = self._build_path("raw_html", folder)
        ext = "json" if self.config.source_type == "json" else "html"
        file_path = path / f"{self.timestamp}_{url_index}.{ext}.gz"
        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            f.write(content)
        logger.warning(f"[{self.config.name}] No listings extracted, saved fallback to {file_path}")
        return file_path

    def download(self, url: str, folder: str | None = None, url_index: int = 0) -> Path | None:
        raw_listings = []
        all_raw_content = []
        current_url = url
        page_number = 1

        raw_content, content = self._fetch_with_raw(current_url)
        all_raw_content.append(raw_content)
        total_pages = self.parser.get_total_pages(content)

        logger.info(f"[{self.config.name}] Starting download, total_pages={total_pages}")

        while current_url and page_number <= total_pages:
            if page_number > 1:
                raw_content, content = self._fetch_with_raw(current_url)
                all_raw_content.append(raw_content)

            for listing in self.parser.extract_listings(content):
                listing["search_url"] = url
                listing["scraped_at"] = datetime.now().isoformat()
                raw_listings.append(listing)

            logger.info(f"[{self.config.name}] Page {page_number}/{total_pages}, total={len(raw_listings)}")
            time.sleep(self.config.rate_limit_seconds)

            page_number += 1
            current_url = self.parser.get_next_page_url(content, current_url, page_number)

        if not raw_listings:
            combined = "\n<!-- PAGE BREAK -->\n".join(all_raw_content)
            self._save_fallback(combined, folder, url_index)
            return None

        return self._save_raw_csv(raw_listings, folder, url_index)
