import time
from datetime import datetime

import pandas as pd

from src.core.normalization import clear_unknown_values, log_unknown_values_summary
from src.core.parser import BaseParser
from src.infrastructure.clients.http_client import CloudscraperHttpClient, HttpClient
from src.logger_setup import get_logger
from src.utils import parse_soup, save_df_to_csv

logger = get_logger(__name__)


class GenericScraper:
    def __init__(self, parser: BaseParser, result_folder: str = "results"):
        self.parser = parser
        self.config = parser.config
        if self.config.use_cloudscraper:
            self.http_client = CloudscraperHttpClient(timeout=60, max_retries=3, retry_delay=3.0)
        else:
            self.http_client = HttpClient(timeout=60, max_retries=3, retry_delay=3.0)
        self.result_folder = result_folder
        self.timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    def fetch_content(self, url: str):
        if self.config.source_type == "json":
            return self.http_client.fetch_json(url)
        html = self.http_client.fetch(url, self.config.encoding)
        return parse_soup(html)

    def scrape(self, start_url: str) -> dict:
        # Clear unknown values tracker at the start of each scrape
        clear_unknown_values()

        raw_listings = []
        current_url = start_url
        page_number = 1

        content = self.fetch_content(current_url)
        total_pages = self.parser.get_total_pages(content)
        logger.info(f"[{self.config.name}] Starting scrape, total_pages={total_pages}")

        while current_url and page_number <= total_pages:
            if page_number > 1:
                content = self.fetch_content(current_url)

            for raw in self.parser.extract_listings(content):
                raw["search_url"] = start_url
                raw["scraped_at"] = datetime.now().isoformat()
                raw_listings.append(raw)

            logger.info(f"[{self.config.name}] Page {page_number}/{total_pages}, found {len(raw_listings)} listings")
            time.sleep(self.config.rate_limit_seconds)

            page_number += 1
            current_url = self.parser.get_next_page_url(content, current_url, page_number)

        raw_df = pd.DataFrame(raw_listings)
        processed_listings = [self.parser.transform_listing(r).model_dump() for r in raw_listings]
        processed_df = pd.DataFrame(processed_listings)

        # Log summary of unknown values encountered during this scrape
        log_unknown_values_summary()

        return {"raw_df": raw_df, "processed_df": processed_df}

    def save_results(
        self, raw_df: pd.DataFrame, processed_df: pd.DataFrame, url_index: int, folder: str = None
    ) -> bool:
        raw_path = f"{self.result_folder}/raw/{self.config.name}"
        processed_path = f"{self.result_folder}/processed/{self.config.name}"

        if folder:
            raw_path = f"{raw_path}/{folder}"
            processed_path = f"{processed_path}/{folder}"

        has_raw_data = save_df_to_csv(raw_df, raw_path, self.timestamp, url_index)
        if has_raw_data:
            save_df_to_csv(processed_df, processed_path, self.timestamp, url_index)

        return has_raw_data
