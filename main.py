import argparse
import os

import pandas as pd

from src.infrastructure.scraper_executor import ScraperExecutor
from src.logger_setup import get_logger
from src.models import PropertyListingData
from src.parsers.homesbg import HomesBgParser
from src.parsers.imotbg import ImotBg
from src.parsers.imotinet import ImotiNetParser
from src.scrapers.homesbg import HomesBgScraper
from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper
from src.utils import get_now_for_filename, save_raw_csv

DEFAULT_TIMEOUT = 10
DEFAULT_ENCODING = "utf-8"
DEFAULT_URL = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/dvustaen/?sid=hY044A"
DEFAULT_OUTPUT_FILE = "imotbg.csv"

logger = get_logger(__name__)

# define enum class fot site type


def convert_to_df(listings: list) -> pd.DataFrame:
    data_dicts = [listing.model_dump() for listing in listings]
    return pd.DataFrame(data_dicts)


def run_imotibg(url, timeout, output_file):
    url = "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bhcl5k&f1=1"

    encoding = "windows-1251"

    scraper = ImotBgScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    res = scraper.process()
    output_file = output_file
    df = convert_to_df(res)

    save_raw_csv(scraper.raw_path_prefix, df)

    df = ImotBg.to_property_listing_df(df)
    df = PropertyListingData.to_property_listing(df)
    file_name = get_now_for_filename()
    df.to_csv(f"data/processed/imotbg/{file_name}.csv", index=False, encoding="utf-8")
    logger.info(f"Saved data to data/processed/imotbg/{file_name}.csv")

    return df


def run_imotinet(url, timeout, output_file):
    url = "https://www.imoti.net/bg/obiavi/r/prodava/sofia--oborishte/dvustaen/?sid=iidgfw"

    encoding = "utf-8"
    scraper = ImotiNetScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )

    res = scraper.process()
    output_file = output_file
    df = convert_to_df(res)
    print(df.columns)
    print(df)
    save_raw_csv(scraper.raw_path_prefix, df)

    df = ImotiNetParser.to_property_listing_df(df)
    df = PropertyListingData.to_property_listing(df)
    file_name = get_now_for_filename()
    df.to_csv(f"data/processed/imotinet/{file_name}.csv", index=False)
    print(df)
    return df


def run_homesbg(url, timeout, output_file):
    url = "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&neighbourhoods%5B%5D=488&typeId=ApartmentSell"

    encoding = "utf-8"
    scraper = HomesBgScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    res = scraper.process()
    output_file = output_file

    df = convert_to_df(res)
    # print(df.columns)
    # print(df)
    save_raw_csv(scraper.raw_path_prefix, df)

    df = HomesBgParser.to_property_listing_df(df)
    df = PropertyListingData.to_property_listing(df)
    file_name = get_now_for_filename()

    output_dir = "data/processed/homesbg"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    df.to_csv(f"data/processed/homesbg/{file_name}.csv", index=False)
    # print(df)
    return df

    # homesbg_mapping = {
    #     "reference_number": "reference_number",  # Map from 'listing_id'
    #     "type": None,  # Not present, add placeholder
    #     "url": "url",
    #     "title": "title",
    #     "location": "location",
    #     "description": "description",
    #     "price": "price",
    #     "photos": "photos",  # Combine from 'photos' and 'num_photos' if needed
    #     "is_favorite": "is_favorite",
    #     "contact_info": "contact_info",  # Map from 'agency_url'
    #     "price_per_m2": "price_per_m2",
    #     "floor": "floor",
    #     "is_top_ad": "is_top_ad",
    # }
    # df = pd.DataFrame(res)
    # df = convert_to_df(res)

    # save_raw_csv(scraper.raw_path_prefix, df)

    # df = df.rename(columns=homesbg_mapping)

    # # Ensure all columns exist
    # required_columns = list(homesbg_mapping.values())
    # for col in required_columns:
    #     if col and col not in df.columns:
    #         df[col] = None

    # df.to_csv(output_file, index=False)
    return df


def concatenate_results(results):
    results = [df.reset_index(drop=True) for df in results]
    # print([i.columns for i in results])
    for i in results:
        print(i.columns, i.shape)
    combined_df = pd.concat(results)
    combined_df.to_csv("combined_results.csv", index=False)
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
