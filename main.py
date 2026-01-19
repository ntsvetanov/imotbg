import argparse
import json
from typing import Optional

import pandas as pd

from src.core.scraper import GenericScraper
from src.logger_setup import get_logger
from src.sites import SITE_PARSERS, get_parser
from src.utils import get_now_for_filename

logger = get_logger(__name__)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", 50)


def scrape_single_url(site_name: str, url: str) -> pd.DataFrame:
    parser = get_parser(site_name)
    scraper = GenericScraper(parser, "")

    result = scraper.scrape(url)
    return result["processed_df"]


def run_site_scraper(
    site_name: str,
    url_configs: list[dict],
    result_folder: str,
    email_client: Optional[object] = None,
) -> pd.DataFrame:
    parser = get_parser(site_name)
    scraper = GenericScraper(parser, result_folder)

    all_processed = []
    failed_urls = []

    for url_index, url_config in enumerate(url_configs):
        url = url_config["url"]
        folder = url_config.get("folder")
        try:
            logger.info(f"[{site_name}] Processing URL {url_index + 1}/{len(url_configs)}")
            result = scraper.scrape(url)

            has_data = scraper.save_results(result["raw_df"], result["processed_df"], url_index, folder)
            if not has_data:
                failed_urls.append(url)
                continue

            all_processed.append(result["processed_df"])

        except Exception as e:
            logger.error(f"[{site_name}] Error processing URL {url}: {e}", exc_info=True)
            failed_urls.append(url)

    if failed_urls and email_client:
        email_client.send_email(
            subject=f"No data for {site_name} - {get_now_for_filename()}",
            text=f"Failed URLs:\n" + "\n".join(failed_urls),
        )

    if not all_processed:
        logger.warning(f"[{site_name}] No data collected")
        return pd.DataFrame()

    return pd.concat(all_processed).reset_index(drop=True)


def load_url_config() -> dict:
    with open("url_configs.json") as f:
        return json.load(f)


def main():
    arg_parser = argparse.ArgumentParser(description="Scrape real estate listings")
    arg_parser.add_argument("--scraper_name", default="all", help="Site name or 'all'")
    arg_parser.add_argument("--result_folder", default="results", help="Output folder")
    arg_parser.add_argument("--url", help="Single URL to scrape (bypasses config, prints to console)")
    arg_parser.add_argument("--save", action="store_true", help="Save results to file when using --url")
    args = arg_parser.parse_args()

    if args.url:
        if args.scraper_name == "all":
            arg_parser.error("--scraper_name is required when using --url")

        if args.save:
            result_df = run_site_scraper(args.scraper_name, [{"url": args.url}], args.result_folder)
            logger.info(f"[{args.scraper_name}] Completed with {len(result_df)} total listings")
        else:
            df = scrape_single_url(args.scraper_name, args.url)
            if df.empty:
                print("No listings found.")
            else:
                display_cols = ["price", "currency", "city", "neighborhood", "property_type", "details_url"]
                available_cols = [c for c in display_cols if c in df.columns]
                print(f"\nFound {len(df)} listings:\n")
                print(df[available_cols].to_string(index=False))
        return

    url_config = load_url_config()
    is_run_all = args.scraper_name == "all"
    sites_to_run = list(SITE_PARSERS.keys()) if is_run_all else [args.scraper_name]

    for site_name in sites_to_run:
        parser = get_parser(site_name)
        site_config = url_config.get(site_name, {})
        url_configs = parser.build_urls(site_config)

        if not url_configs:
            logger.warning(f"No URLs configured for {site_name}")
            continue

        result_df = run_site_scraper(site_name, url_configs, args.result_folder)
        logger.info(f"[{site_name}] Completed with {len(result_df)} total listings")


if __name__ == "__main__":
    main()
