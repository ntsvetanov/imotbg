import argparse
import os

import pandas as pd

from src.infrastructure.clients.email_client import EmailClient
from src.infrastructure.scraper_executor import ScraperExecutor
from src.logger_setup import get_logger
from src.scrapers.homesbg import HomesBgScraper
from src.scrapers.imotbg import ImotBgScraper
from src.scrapers.imotinet import ImotiNetScraper
from src.utils import get_now_date, get_now_for_filename

DEFAULT_TIMEOUT = 30
DEFAULT_ENCODING = "utf-8"
DEFAULT_OUTPUT_FILE = "data"

logger = get_logger(__name__)

email_client = EmailClient()


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
        "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjaqz2&f1=1",
        "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjarb7&f1=1",
        "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bjarj1&f1=1",
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
        is_saved = scraper.save_raw_data(url_idx)
        if not is_saved:
            email_client.send_email(
                subject=f"No data available for ImotBg {get_now_date()}",
                text=f"No data available for \nImotBg on {date_for_name}\nurl {url} with url_idx {url_idx}",
            )
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
        "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=gzSTlT",
    ]
    scraper = initialize_scraper(
        scraper_class=ImotiNetScraper,
        timeout=timeout,
        result_folder=result_folder,
        date_for_name=date_for_name,
    )

    results = []
    for url_idx, url in enumerate(urls):
        logger.info(f"Processing Imoti Net URL: {url}")
        df = scraper.process(url=url)
        is_saved = scraper.save_raw_data(url_idx)
        if not is_saved:
            email_client.send_email(
                subject=f"No data available for ImotBg {get_now_date()}",
                text=f"No data available for \nImotBg on {date_for_name}\nurl {url} with url_idx {url_idx}",
            )
        scraper.save_processed_data(url_idx)
        results.append(df)

    return pd.concat(results).reset_index(drop=True)


def run_homesbg(
    timeout: int,
    result_folder: str,
    date_for_name: str,
):
    NEIGHBORHOOD_IDS = [
        487,  # Оборище
        526,  # Хиподрума
        421,  # Иван Вазов
        527,  # Хладилника
        515,  # Стрелбище
        424,  # Изток
        423,  # Изгрев
        503,  # Редута
        517,  # Сухата Река
        437,  # Медицинска академия
    ]

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
    url_idx = 0
    is_saved = scraper.save_raw_data(url_idx)
    if not is_saved:
        email_client.send_email(
            subject=f"No data available for ImotBg {get_now_date()}",
            text=f"No data available for \nImotBg on {date_for_name}\nurl {url} with url_idx {url_idx}",
        )
    scraper.save_processed_data()
    return df


def concatenate_results(
    results,
    result_folder,
    date_for_name,
):
    output_path = os.path.join(result_folder, f"{date_for_name}_all_results.csv")
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
    result_df = concatenate_results(results, result_folder, date_for_name)
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
