import os
from typing import Optional

import pandas as pd

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.models import PropertyListingData
from src.parsers.imotbg import ImotBgParser
from src.utils import (
    convert_to_df,
    get_now_for_filename,
    save_df_to_csv,
)

logger = get_logger(__name__)

DEFAULT_HEADERS = None


class ImotBgScraper:
    def __init__(
        self,
        url: str,
        encoding: str = "windows-1251",
        headers: Optional[dict] = None,
        timeout: int = 10,
        raw_path_prefix="",
        process_path_prefix="",
    ):
        self.url = url
        self.encoding = encoding

        if headers is None:
            headers = DEFAULT_HEADERS

        if not raw_path_prefix:
            raw_path_prefix = os.path.join("data", "raw", "imotbg")

        if not process_path_prefix:
            process_path_prefix = os.path.join("data", "processed", "imotbg")

        self.http_client = HttpClient(
            headers=headers,
            timeout=timeout,
        )

        self.parser = ImotBgParser()

        self.total_pages = -1

        self.raw_path_prefix = raw_path_prefix
        self.process_path_prefix = process_path_prefix

    def fetch_page(self, url: str) -> str:
        try:
            return self.http_client.fetch(
                url=url,
                encoding=self.encoding,
            )
        except Exception:
            logger.error(f"Failed to fetch page {url}", exc_info=True)
            raise

    def process(self, output_file) -> pd.DataFrame:
        html_content = self.fetch_page(self.url)
        if self.total_pages == -1:
            self.total_pages = self.parser.get_total_pages(html_content)

        results = []
        for page_num in range(1, self.total_pages + 1):
            page_url = self.url.replace("f1=1", f"f1={page_num}")
            html_content = self.fetch_page(page_url)
            logger.info(f"Processing {page_url} page {page_num} of {self.total_pages}")
            processed_listings = self.parser.parse_listings(html_content)
            results.extend(processed_listings)

        df = convert_to_df(results)
        date_for_name = get_now_for_filename()
        save_df_to_csv(
            self.raw_path_prefix,
            date_for_name,
            df,
        )

        df = self.parser.to_property_listing_df(df)
        df = PropertyListingData.to_property_listing(df)
        save_df_to_csv(
            self.process_path_prefix,
            date_for_name,
            df,
        )

        return df
