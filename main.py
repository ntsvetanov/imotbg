import argparse

import pandas as pd

from src.infrastructure.scraper_executor import ScraperExecutor
from src.scrapers.homesbg import HomesBgScraper
from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper

DEFAULT_TIMEOUT = 10
DEFAULT_ENCODING = "utf-8"
DEFAULT_URL = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/dvustaen/?sid=hY044A"
DEFAULT_OUTPUT_FILE = "imotbg.csv"


def run_imotibg(url, timeout, output_file):
    url = "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bhcl5k&f1=1"

    encoding = "windows-1251"
    scraper = ImotBgScraper(
        url=url,
        encoding=encoding,
        timeout=timeout,
    )
    res = scraper.process()
    output_file = "imotbg.csv"
    df = pd.DataFrame(res)

    imotibg_mapping = {
        "reference_number": "reference_number",
        "type": None,  # Not present, add placeholder
        "url": "url",  # Map directly or rename from 'details_url'
        "title": "title",
        "location": "location",
        "description": "description",
        "price": "price",
        "photos": "photos",  # Remove duplicate 'photos' column
        "is_favorite": "is_favorite",
        "contact_info": "contact_info",  # Map from 'agency'
        "price_per_m2": "price_per_m2",
        "floor": "floor",
        "is_top_ad": "is_top_ad",
    }

    df = df.rename(columns=imotibg_mapping)

    # Ensure all columns exist
    required_columns = list(imotibg_mapping.values())
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    df.to_csv(output_file, index=False)
    return df


def clean_imotinet(df):
    df["property_type"] = df["title"].str.split(",").str[0].str.strip()
    df["area"] = df["title"].str.split(",").str[1].str.extract(r"(\d+)").astype(float)

    df["price_float"] = df["price"].str.extract(r"([\d\s]+)").replace("\s+", "", regex=True).astype(float)
    df["currency"] = df["price"].str.extract(r"(EUR|USD|BGN)")[0]

    df[["city", "neighbourhood"]] = df["location"].str.split(", ", expand=True)
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
    output_file = "imotinet.csv"

    imotinet_mapping = {
        "reference_number": "reference_number",  # Map from 'id'
        "type": None,  # Not present, add placeholder
        "url": "url",  # Map directly or rename from 'details_url'
        "title": "title",
        "location": "location",
        "description": "description",
        "price": "price",
        "photos": "photos",  # Map from 'images'
        "is_favorite": "is_favorite",
        "contact_info": "contact_info",  # Map from 'agency'
        "price_per_m2": "price_per_m2",  # Add placeholder if missing
        "floor": "floor",  # Add placeholder if missing
        "is_top_ad": "is_top_ad",  # Add placeholder if missing
    }
    df = pd.DataFrame(res)
    df = df.rename(columns=imotinet_mapping)

    # Ensure all columns exist
    required_columns = list(imotinet_mapping.values())
    for col in required_columns:
        if col and col not in df.columns:
            df[col] = None

    df.to_csv(output_file, index=False)

    df = clean_imotinet(df)
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
    output_file = "homesbg.csv"

    homesbg_mapping = {
        "reference_number": "reference_number",  # Map from 'listing_id'
        "type": None,  # Not present, add placeholder
        "url": "url",
        "title": "title",
        "location": "location",
        "description": "description",
        "price": "price",
        "photos": "photos",  # Combine from 'photos' and 'num_photos' if needed
        "is_favorite": "is_favorite",
        "contact_info": "contact_info",  # Map from 'agency_url'
        "price_per_m2": "price_per_m2",
        "floor": "floor",
        "is_top_ad": "is_top_ad",
    }
    df = pd.DataFrame(res)
    df = df.rename(columns=homesbg_mapping)

    # Ensure all columns exist
    required_columns = list(homesbg_mapping.values())
    for col in required_columns:
        if col and col not in df.columns:
            df[col] = None

    df.to_csv(output_file, index=False)
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

    results = executor.run()
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
