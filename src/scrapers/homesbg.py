import os
from typing import Dict, List, Optional

import pandas as pd

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.models import PropertyListingData
from src.parsers.homesbg import HomesBgParser
from src.utils import convert_to_df, get_now_for_filename, save_df_to_csv

logger = get_logger(__name__)

DEFAULT_HEADERS = None


class HomesBgScraper:
    def __init__(
        self,
        url: str,
        encoding: str = "utf-8",
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
            raw_path_prefix = os.path.join("data", "raw", "homesbg")

        if not process_path_prefix:
            process_path_prefix = os.path.join("data", "processed", "homesbg")

        self.http_client = HttpClient(
            headers=headers,
            timeout=timeout,
        )

        self.parser = HomesBgParser()

        self.total_pages = -1

        self.raw_path_prefix = raw_path_prefix
        self.process_path_prefix = process_path_prefix

    def fetch_data(self) -> Dict:
        try:
            response = self.http_client.fetch_json(self.url)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch data from {self.url}: {e}", exc_info=True)
            return {}

    def process(self, output_file) -> List[Dict]:
        try:
            results = []
            start_index = 0
            stop_index = 100
            increment = 100
            cnt = 0
            url = self.url
            offers_count = 10000
            max_pages = 30

            while True:
                self.url = f"{url}&startIndex={start_index}&stopIndex={stop_index}"
                logger.info(f"Fetching data from: {self.url}")
                data = self.fetch_data()
                if offers_count == 10000:
                    offers_count = data.get("offersCount", 10000)
                    logger.info(f"Offers count: {offers_count}")

                if not data:
                    logger.info("No data available.")
                    break
                if not data.get("result"):
                    logger.info("No more results available.")
                    break
                if offers_count < stop_index:
                    logger.info("No more results available.")
                    break

                results.extend(self.parser.parse_listings(data))

                if not data.get("hasMoreItems", False):
                    break

                start_index += increment
                stop_index += increment
                cnt += 1
                if cnt > max_pages:
                    break

            df = convert_to_df(results)
            date_for_name = get_now_for_filename()
            save_df_to_csv(self.raw_path_prefix, date_for_name, df)

            df = self.parser.to_property_listing_df(df)
            df = PropertyListingData.to_property_listing(df)
            save_df_to_csv(self.process_path_prefix, date_for_name, df)

            return df
        except Exception as e:
            logger.error(f"Error processing all data: {e}", exc_info=True)
            return pd.DataFrame()
