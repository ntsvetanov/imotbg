from typing import Dict, List, Optional

from src.infrastructure.clients.http_client import HttpClient
from src.logger_setup import get_logger
from src.parsers.homesbg import HomesbgParser

logger = get_logger(__file__)


class HomesBgScraper:
    def __init__(
        self,
        url: str,
        encoding: str = "windows-1251",
        headers: Optional[dict] = None,
        timeout: int = 10,
    ):
        self.url = url
        self.http_client = HttpClient(headers=headers, timeout=timeout)
        self.parser = HomesbgParser()

    def fetch_data(self) -> Dict:
        try:
            response = self.http_client.fetch_json(self.url)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch data from {self.url}: {e}", exc_info=True)
            return {}

    def process(self) -> List[Dict]:
        print("self.url = ", self.url)
        try:
            results = []
            start_index = 0
            stop_index = 100
            increment = 100
            cnt = 0
            url = self.url
            offers_count = 10000

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
                if cnt > 20:
                    break

            return results
        except Exception as e:
            logger.error(f"Error processing all data: {e}", exc_info=True)
            return []
