import argparse
import os

import pandas as pd

from src.infrastructure.scraper_executor import ScraperExecutor
from src.logger_setup import get_logger
from src.scrapers.homesbg import HomesBgScraper
from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper

DEFAULT_TIMEOUT = 10
DEFAULT_ENCODING = "utf-8"
DEFAULT_URL = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/dvustaen/?sid=hY044A"
DEFAULT_OUTPUT_FILE = "imotbg.csv"

logger = get_logger(__name__)


def run_imotibg(url, timeout, output_file):
    url = "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bi18s2&f1=1"

    encoding = "windows-1251"

    scraper = ImotBgScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    df = scraper.process(output_file)
    return df


def run_imotinet(url, timeout, output_file):
    url = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=h892j0"

    encoding = "utf-8"
    scraper = ImotiNetScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    df = scraper.process(output_file)
    return df


def run_homesbg(url, timeout, output_file):
    neighborhood_ids = [
        487,  # Oborishte
        527,  # Hladilnika
        424,  # Iztok
    ]
    neighborhood_ids = ",".join(str(id) for id in neighborhood_ids)
    url = f"https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&neighbourhoods%5B%5D={neighborhood_ids}&typeId=ApartmentSell"

    encoding = "utf-8"
    scraper = HomesBgScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    df = scraper.process(output_file)
    return df


def concatenate_results(results):
    results = [df.reset_index(drop=True) for df in results]
    combined_df = pd.concat(results)
    path = os.path.join("data", "combined_results.csv")
    combined_df.to_csv(path, index=False)
    return combined_df


def main(url, timeout, encoding, output_file):
    # todo add endocing
    executor = ScraperExecutor(timeout)

    executor.add_task(run_imotibg, url, timeout, "imotbg.csv")
    executor.add_task(run_imotinet, url, timeout, "imotinet.csv")
    executor.add_task(run_homesbg, url, timeout, "homesbg.csv")

    results = executor.run()  # noqa
    concatenate_results(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape data from Imot.bg and save it to a CSV file.")
    parser.add_argument(
        "--url",
        "-u",
        type=str,
        help="Base URL for scraping (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default=DEFAULT_ENCODING,
        help="Encoding for the scraper (default: %(default)s)",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help="Output CSV file (default: %(default)s)",
    )

    args = parser.parse_args()

    main(
        url=args.url,
        timeout=args.timeout,
        encoding=args.encoding,
        output_file=args.output_file,
    )
