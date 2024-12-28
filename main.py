import argparse
import enum
from datetime import datetime
from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, HttpUrl, ValidationError, validator

from src.infrastructure.scraper_executor import ScraperExecutor
from src.logger_setup import get_logger
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


class Site(enum.Enum):
    IMOTBG = "imot.bg"
    IMOTINET = "imoti.net"
    HOMESBG = "homes.bg"


class PropertyListingData(BaseModel):
    title: Optional[str] = ""
    price: Optional[int] = 0
    currency: Optional[str] = ""
    offer_type: Optional[str] = ""
    property_type: Optional[str] = ""
    city: Optional[str] = ""
    neighborhood: Optional[str] = ""
    description: Optional[str] = ""
    contact_info: Optional[str] = ""
    agency_url: Optional[HttpUrl] = ""
    details_url: Optional[HttpUrl] = ""
    num_photos: Optional[int] = 0
    date_added: Optional[datetime] = None
    site: Site
    floor: Optional[int] = 0
    price_per_m2: Optional[float] = 0.0
    ref_no: Optional[str] = ""

    model_config = ConfigDict(use_enum_values=True)

    @validator("price", pre=True)
    def validate_price(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return 0
        return int(value) if isinstance(value, (int, str)) else value

    @validator("currency", pre=True)
    def validate_currency(cls, value):
        if value is None or (isinstance(value, float) and value != value):
            return "unknown"
        return str(value)


def convert_to_df(listings: list) -> pd.DataFrame:
    data_dicts = [listing.model_dump() for listing in listings]
    return pd.DataFrame(data_dicts)


def validate_property_listing_data(df):
    valid_rows = []

    for _, row in df.iterrows():
        try:
            validated_data = PropertyListingData(**row.to_dict())
            valid_rows.append(validated_data.dict())
        except ValidationError:
            logger.error(f"Invalid row: {row.to_dict()}", exc_info=True)

    valid_df = pd.DataFrame(valid_rows)

    return valid_df


def clean_imotibg(df):
    df.columns = [f"imotbg_{i}" for i in df.columns]
    try:
        df["price"] = (
            df["imotbg_price"].str.extract(r"([\d\s]+)").replace(r"\s+", "", regex=True).astype(int, errors="ignore")
        )
        df["currency"] = df["imotbg_price"].str.extract(r"(EUR|USD|BGN)")[0]

        df["offer_type"] = df["imotbg_title"].str.split(" ").str[0].str.strip()
        df["property_type"] = df["imotbg_title"].str.split(" ").str[1].str.strip()

        df["city"] = df["imotbg_location"].str.split(",").str[0].str.strip()
        df["neighborhood"] = df["imotbg_location"].str.split(",").str[1].str.strip()

        df["description"] = df["imotbg_description"]
        df["contact_info"] = df["imotbg_contact_info"]
        df["agency_url"] = df["imotbg_agency_url"]
        df["details_url"] = df["imotbg_details_url"]
        df["num_photos"] = df["imotbg_num_photos"]
        df["date_added"] = df["imotbg_date_added"]
        df["title"] = df["imotbg_title"]
        df["site"] = Site.IMOTBG
        df["floor"] = -1
        df["price_per_m2"] = -1

    except Exception as e:
        logger.error(f"Error cleaning imotibg data: {e}", exc_info=True)

    df = validate_property_listing_data(df)
    return df


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

    df = clean_imotibg(df)
    file_name = get_now_for_filename()
    df.to_csv(f"data/processed/imotbg/{file_name}.csv", index=False)

    return df


def clean_imotinet(df):
    try:
        df["title"] = df["title"]

        df["offer_type"] = df["title"].str.split(" ").str[0].str.strip()
        df["property_type"] = df["title"].str.split(" ").str[1].str.strip()

        df["price"] = (
            df["price_and_currency"]
            .str.extract(r"([\d\s]+)")
            .replace(r"\s+", "", regex=True)
            .astype(int, errors="ignore")
        )
        df["currency"] = df["price_and_currency"].str.extract(r"(EUR|USD|BGN)")[0]

        df["city"] = df["location"].str.split(",").str[0].str.strip()
        df["neighborhood"] = df["location"].str.split(",").str[1].str.strip()

        df["description"] = df["description"]
        df["agency_url"] = df["agency"]

        df["details_url"] = df["details_url"]
        df["num_photos"] = df["num_photos"]
        df["date_added"] = df["date_added"]
        df["site"] = Site.IMOTINET
        df["floor"] = df["floor"]
        df["price_per_m2"] = df["price_per_m2"]
        df["ref_no"] = df["reference_number"]

    except Exception as e:
        logger.error(f"Error cleaning imotinet data: {e}", exc_info=True)

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

    df = clean_imotinet(df)

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
    df = convert_to_df(res)

    save_raw_csv(scraper.raw_path_prefix, df)

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

    # executor.add_task(run_imotibg, url, timeout, "imotbg_old.csv")
    executor.add_task(run_imotinet, url, timeout, "imotinet.csv")
    # executor.add_task(run_homesbg, url, timeout, "homesbg.csv")

    results = executor.run()  # noqa
    # concatenate_results(results)


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
