import os
from typing import Dict, List, Optional

import pandas as pd

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.models import PropertyListingData
from src.parsers.homesbg import HomesBgParser
from src.utils import convert_to_df, save_df_to_csv

logger = get_logger(__name__)

DEFAULT_HEADERS = None


class HomesBgScraper:
    def __init__(
        self,
        date_for_name: str,
        encoding: str = "utf-8",
        headers: Optional[dict] = None,
        timeout: int = 10,
        result_folder="data",
        raw_file_path="raw",
        process_file_path="processed",
        site_name="homesbg",
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

        self.parser = HomesBgParser()

        self.total_pages = -1

    def fetch_data(self, url) -> Dict:
        try:
            response = self.http_client.fetch_json(url)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}", exc_info=True)
            return {}

    def process(self, url) -> List[Dict]:
        try:
            results = []
            start_index = 0
            stop_index = 100
            increment = 100
            cnt = 0
            url = url
            offers_count = 20000
            max_pages = 30

            while True:
                # re-pace startIndex and stopIndex

                url_with_indices = f"{url}&startIndex={start_index}&stopIndex={stop_index}"
                logger.info(f"Fetching data from: {url_with_indices}")
                data = self.fetch_data(url_with_indices)
                if offers_count == 20000:
                    offers_count = data.get("offersCount", 20000)
                    logger.info(f"Offers count: {offers_count}")

                if not data:
                    logger.info("No data available.")
                    break
                if not data.get("result"):
                    logger.info("No more results available.")
                    break

                results.extend(self.parser.parse_listings(data, url))

                if not data.get("hasMoreItems", False):
                    break

                start_index += increment
                stop_index += increment
                cnt += 1
                if cnt > max_pages:
                    break

            df = convert_to_df(results)
            self.raw_df = df.copy()
            df = self.parser.to_property_listing_df(df)
            df = PropertyListingData.to_property_listing(df)
            self.df = df

            return df
        except Exception as e:
            logger.error(f"Error processing all data: {e}", exc_info=True)
            return pd.DataFrame()

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
