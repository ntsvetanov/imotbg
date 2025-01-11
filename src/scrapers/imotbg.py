import os
import time
from typing import Optional

import pandas as pd

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.models import PropertyListingData
from src.parsers.imotbg import ImotBgParser
from src.utils import (
    convert_to_df,
    save_df_to_csv,
)

logger = get_logger(__name__)

DEFAULT_HEADERS = None


class ImotBgScraper:
    def __init__(
        self,
        date_for_name: str,
        encoding: str = "windows-1251",
        headers: Optional[dict] = None,
        timeout: int = 10,
        result_folder="data",
        raw_file_path="raw",
        process_file_path="processed",
        site_name="imotbg",
    ):
        self.date_for_name = date_for_name
        self.encoding = encoding

        if headers is None:
            headers = DEFAULT_HEADERS

        self.raw_file_path = os.path.join(result_folder, raw_file_path, site_name)
        self.process_file_path = os.path.join(result_folder, process_file_path, site_name)
        self.site_name = site_name

        self.http_client = HttpClient(
            headers=headers,
            timeout=timeout,
        )

        self.parser = ImotBgParser()

    def fetch_page(self, url: str) -> str:
        try:
            data = self.http_client.fetch(
                url=url,
                encoding=self.encoding,
            )
            time.sleep(1)
            return data
        except Exception:
            logger.error(f"Failed to fetch page {url}", exc_info=True)
            raise

    def process(self, url) -> pd.DataFrame:
        html_content = self.fetch_page(url)
        total_pages = self.parser.get_total_pages(html_content)

        results = []
        for page_num in range(1, total_pages + 1):
            page_url = url.replace("f1=1", f"f1={page_num}")
            html_content = self.fetch_page(page_url)
            logger.info(f"Processing {page_url} page {page_num} of {total_pages}")
            processed_listings = self.parser.parse_listings(
                page_content=html_content,
                search_url=page_url,
            )
            results.extend(processed_listings)

        total_offers = len(results)
        raw_df = convert_to_df(results)
        raw_df["total_offers"] = total_offers
        self.raw_df = raw_df.copy()

        df = self.parser.to_property_listing_df(raw_df)
        df = PropertyListingData.to_property_listing(df)
        self.df = df

        return df

    def save_raw_data(self, url_idx=0):
        return save_df_to_csv(
            df=self.raw_df,
            result_data_path=self.raw_file_path,
            date_for_name=self.date_for_name,
            url_idx=url_idx,
        )

    def save_processed_data(self, url_idx=0):
        save_df_to_csv(
            df=self.df,
            result_data_path=self.process_file_path,
            date_for_name=self.date_for_name,
            url_idx=url_idx,
        )
