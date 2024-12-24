import argparse

import pandas as pd

from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper

DEFAULT_TIMEOUT = 10
DEFAULT_ENCODING = "utf-8"
DEFAULT_URL = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/dvustaen/?sid=hY044A"
DEFAULT_OUTPUT_FILE = "imotbg.csv"


def run_imotibg(url, timeout, output_file):
    encoding = "windows-1251"
    scraper = ImotBgScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    res = scraper.process()

    pd.DataFrame(res).to_csv(output_file, index=False)


def run_imotinet(url, timeout, output_file):
    encoding = "utf-8"
    scraper = ImotiNetScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    res = res = scraper.process()
    pd.DataFrame(res).to_csv(output_file, index=False)


def main(url, timeout, encoding, output_file):
    # todo add endocing
    run_imotinet(url, timeout, output_file)


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
