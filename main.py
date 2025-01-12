import argparse
import os
from typing import List, Type

import pandas as pd

from src.infrastructure.clients.email_client import EmailClient
from src.infrastructure.scraper_executor import ScraperExecutor
from src.logger_setup import get_logger
from src.scrapers.homesbg import HomesBgScraper
from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper
from src.utils import get_now_date, get_now_for_filename

DEFAULT_TIMEOUT = 300
DEFAULT_ENCODING = "utf-8"
DEFAULT_OUTPUT_FILE = "data"
logger = get_logger(__name__)

email_client = EmailClient()

# TODO add named filter by neighborhood and add it to name of the csv
# TODO main property type
# TODO make one generic scraper class and use dependency injection to pass the parser

# Configuration Constants
IMOT_BG_URLS = [
    "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjaqz2&f1=1",
    "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjarb7&f1=1",
    "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjarj1&f1=1",
    "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjri0i&f1=1",
]
IMOTI_NET_URLS = [
    "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=gFM8jD",
    "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=iKI3oo",
]
HOMES_BG_NEIGHBORHOODS = [487, 526, 421, 527, 515, 424, 423, 503, 517, 437, 447, 403, 412]
HOMES_BG_URL_TEMPLATE = "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&typeId=ApartmentSell"


def initialize_scraper(
    scraper_class: Type,
    date_for_name: str,
    timeout: int,
    result_folder: str,
):
    return scraper_class(
        date_for_name=date_for_name,
        timeout=timeout,
        result_folder=result_folder,
    )


def run_scraper(
    scraper_class: Type,
    urls: List[str],
    timeout: int,
    result_folder: str,
    date_for_name: str,
    scraper_name: str,
):
    scraper = initialize_scraper(scraper_class, date_for_name, timeout, result_folder)

    results = []
    email_msg = []
    for url_idx, url in enumerate(urls):
        try:
            logger.info(f"Processing {scraper_name} URL: {url}")
            df = scraper.process(url=url)
            if not scraper.save_raw_data(url_idx):
                email_msg.append(
                    f"No data available for {scraper_name} on {date_for_name}\nurl {url} (index {url_idx})"
                )
                continue
            scraper.save_processed_data(url_idx)
            results.append(df)
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}", exc_info=True)

    if email_msg:
        email_client.send_email(
            subject=f"No data available for {scraper_name} {get_now_date()}",
            text="\n".join(email_msg),
        )
    if not results:
        logger.warning(f"No data available for {scraper_name}")
        return pd.DataFrame()
    return pd.concat(results).reset_index(drop=True)


def get_homes_bg_urls():
    urls = [f"{HOMES_BG_URL_TEMPLATE}&neighbourhoods%5B%5D={n}" for n in HOMES_BG_NEIGHBORHOODS]
    urls.append("https://www.homes.bg/api/offers??currencyId=1&filterOrderBy=0&locationId=0&typeId=LandAgro")
    return urls


def concatenate_results(results: List[pd.DataFrame], result_folder: str, date_for_name: str):
    output_path = os.path.join(result_folder, f"{date_for_name}_all_results.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_df = pd.concat(results).reset_index(drop=True)
    combined_df.to_csv(output_path, index=False)
    return combined_df


def main(timeout: int, result_folder: str):
    date_for_name = get_now_for_filename()
    executor = ScraperExecutor(timeout)

    executor.add_task(run_scraper, ImotBgScraper, IMOT_BG_URLS, timeout, result_folder, date_for_name, "ImotBg")
    executor.add_task(run_scraper, ImotiNetScraper, IMOTI_NET_URLS, timeout, result_folder, date_for_name, "ImotiNet")
    executor.add_task(
        run_scraper, HomesBgScraper, get_homes_bg_urls(), timeout, result_folder, date_for_name, "HomesBg"
    )

    results = executor.run()
    logger.info(f"Executor completed with results: {results}")
    for result in results:
        logger.info(f"Result type: {type(result)} | Result preview: {result.shape}")

    try:
        result_df = concatenate_results(results, result_folder, date_for_name)
        logger.info(f"Scraping completed. Combined results {result_df.shape} saved to {result_folder} ")
    except ValueError:
        logger.warning("No data to concatenate. No results saved.")
    except Exception as e:
        logger.error(f"Error saving results: {e}", exc_info=True)


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
        help="Output folder for CSV files (default: %(default)s)",
    )

    args = parser.parse_args()
    main(timeout=args.timeout, result_folder=args.result_folder)
