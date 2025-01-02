import argparse
import os

import pandas as pd

from src.infrastructure.scraper_executor import ScraperExecutor
from src.logger_setup import get_logger
from src.scrapers.homesbg import HomesBgScraper
from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper
from src.utils import get_now_for_filename

DEFAULT_TIMEOUT = 30
DEFAULT_ENCODING = "utf-8"
DEFAULT_OUTPUT_FILE = "data"

logger = get_logger(__name__)


def initialize_scraper(
    scraper_class,
    date_for_name,
    timeout,
    result_folder,
):
    return scraper_class(
        date_for_name=date_for_name,
        timeout=timeout,
        result_folder=result_folder,
    )


def run_imotibg(
    timeout: int,
    result_folder: str,
    date_for_name: str,
):
    urls = [
        "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bi18s2&f1=1",
    ]
    scraper = initialize_scraper(
        scraper_class=ImotBgScraper,
        timeout=timeout,
        result_folder=result_folder,
        date_for_name=date_for_name,
    )

    results = []
    for url_idx, url in enumerate(urls):
        logger.info(f"Processing Imot Bg URL: {url}")
        df = scraper.process(url=url)
        scraper.save_raw_data(url_idx)
        scraper.save_processed_data(url_idx)
        results.append(df)

    return pd.concat(results).reset_index(drop=True)


def run_imotinet(
    timeout: int,
    result_folder: str,
    date_for_name: str,
):
    urls = [
        "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=h892j0",
    ]
    scraper = initialize_scraper(
        scraper_class=ImotiNetScraper,
        timeout=timeout,
        result_folder=result_folder,
        date_for_name=date_for_name,
    )

    results = []
    for idx, url in enumerate(urls):
        logger.info(f"Processing Imoti Net URL: {url}")
        df = scraper.process(url=url)
        scraper.save_raw_data(idx)
        scraper.save_processed_data(idx)
        results.append(df)

    return pd.concat(results).reset_index(drop=True)


def run_homesbg(
    timeout: int,
    result_folder: str,
    date_for_name: str,
):
    NEIGHBORHOOD_IDS = [487, 527, 424]
    neighborhood_ids = ",".join(map(str, NEIGHBORHOOD_IDS))
    HOMES_BG_URL_TEMPLATE = "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&neighbourhoods%5B%5D={neighborhoods}&typeId=ApartmentSell"
    url = HOMES_BG_URL_TEMPLATE.format(neighborhoods=neighborhood_ids)

    logger.info(f"Processing Homes Bg URL: {url}")
    scraper = initialize_scraper(
        scraper_class=HomesBgScraper,
        timeout=timeout,
        result_folder=result_folder,
        date_for_name=date_for_name,
    )
    df = scraper.process(url=url)
    scraper.save_raw_data()
    scraper.save_processed_data()
    return df


def concatenate_results(results, result_folder):
    output_path = os.path.join(result_folder, "combined_results.csv")
    combined_df = pd.concat(results).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_df.to_csv(output_path, index=False)
    return combined_df


def main(
    timeout: int,
    result_folder: str,
):
    date_for_name = get_now_for_filename()

    executor = ScraperExecutor(timeout)

    executor.add_task(run_imotibg, timeout, result_folder, date_for_name)
    executor.add_task(run_imotinet, timeout, result_folder, date_for_name)
    executor.add_task(run_homesbg, timeout, result_folder, date_for_name)

    results = executor.run()
    result_df = concatenate_results(results, result_folder)
    logger.info(f"Scraping completed. Combined {result_df.shape}results saved to {result_folder}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape real estate data and save it to a CSV file.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--result_folder",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help="Output CSV file path (default: %(default)s)",
    )

    args = parser.parse_args()

    main(
        timeout=args.timeout,
        result_folder=args.result_folder,
    )
