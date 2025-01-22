import argparse
import json
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

from enum import Enum


class ScraperName(Enum):
    IMOT_BG = "ImotBg"
    IMOTI_NET = "ImotiNet"
    HOMES_BG = "HomesBg"


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


def get_homes_bg_urls(urls_ids):
    HOMES_BG_URL_TEMPLATE = (
        "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&typeId=ApartmentSell"
    )
    urls = [f"{HOMES_BG_URL_TEMPLATE}&neighbourhoods%5B%5D={n}" for n in urls_ids]
    urls.append("https://www.homes.bg/api/offers??currencyId=1&filterOrderBy=0&locationId=0&typeId=LandAgro")
    return urls


def concatenate_results(results: List[pd.DataFrame], result_folder: str, date_for_name: str):
    output_path = os.path.join(result_folder, f"{date_for_name}_all_results.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_df = pd.concat(results).reset_index(drop=True)
    combined_df.to_csv(output_path, index=False)
    return combined_df


def run_all_scrapers(
    url_config,
    result_folder: str,
):
    date_for_name = get_now_for_filename()
    timeout = DEFAULT_TIMEOUT
    executor = ScraperExecutor(timeout)

    executor.add_task(
        run_scraper,
        ImotBgScraper,
        url_config.get(ScraperName.IMOT_BG.value),
        timeout,
        result_folder,
        date_for_name,
        ScraperName.IMOT_BG.value,
    )
    executor.add_task(
        run_scraper,
        ImotiNetScraper,
        url_config.get(ScraperName.IMOTI_NET.value),
        timeout,
        result_folder,
        date_for_name,
        ScraperName.IMOTI_NET.value,
    )
    executor.add_task(
        run_scraper,
        HomesBgScraper,
        get_homes_bg_urls(url_config.get(ScraperName.HOMES_BG.value)),
        timeout,
        result_folder,
        date_for_name,
        ScraperName.HOMES_BG.value,
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


def run_scraper_by_site_name(
    urls: list,
    scraper_name: str,
    result_folder: str,
):
    date_for_name = get_now_for_filename()
    timeout = DEFAULT_TIMEOUT

    scraper_map = {
        "ImotBg": ImotBgScraper,
        "ImotiNet": ImotiNetScraper,
        "HomesBg": HomesBgScraper,
    }

    scraper_class = scraper_map[scraper_name]

    result = run_scraper(
        scraper_class,
        urls,
        timeout,
        result_folder,
        date_for_name,
        scraper_name,
    )

    if not result.empty:
        logger.info(f"{scraper_name} results saved successfully.")
    else:
        logger.warning(f"{scraper_name} returned no results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape real estate data and save it to a CSV file.")

    parser.add_argument(
        "--result_folder",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help="Output folder for CSV files (default: %(default)s)",
    )

    parser.add_argument(
        "--scraper_name",
        type=str,
        default="all",
        help="Name of the scraper to run (default: %(default)s)",
    )

    with open("url_configs.json", "r") as file:
        url_config = json.load(file)

    scraper_name = parser.parse_args().scraper_name
    if scraper_name != "all":
        logger.info(f"Running scraper for {scraper_name}")
        site_url_config = url_config.get(scraper_name, None)

        if not site_url_config:
            logger.error(f"Scraper {scraper_name} not found in url_configs.json")
            exit(1)

        if scraper_name == "HomesBg":
            site_url_config = get_homes_bg_urls(site_url_config)

        run_scraper_by_site_name(
            urls=site_url_config,
            scraper_name=scraper_name,
            result_folder=parser.parse_args().result_folder,
        )
        exit(0)

    args = parser.parse_args()

    run_all_scrapers(
        url_config=url_config,
        result_folder=args.result_folder,
    )
