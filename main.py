import argparse
import json
from typing import Protocol

import pandas as pd

from src.core.reprocessor import reprocess_raw_data
from src.core.scraper import GenericScraper
from src.logger_setup import get_logger
from src.sites import SITE_PARSERS, get_parser
from src.utils import get_now_for_filename

logger = get_logger(__name__)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", 50)


class EmailSender(Protocol):
    """Protocol for email sending capability."""

    def send_email(self, subject: str, text: str) -> None: ...


def scrape_single_url(site_name: str, url: str) -> pd.DataFrame:
    """Scrape a single URL and return the processed DataFrame."""
    parser = get_parser(site_name)
    scraper = GenericScraper(parser, "")
    result = scraper.scrape(url)
    return result["processed_df"]


def run_site_scraper(
    site_name: str,
    url_configs: list[dict],
    result_folder: str,
    email_client: EmailSender | None = None,
) -> pd.DataFrame:
    """Run scraper for a site with multiple URL configurations."""
    parser = get_parser(site_name)
    scraper = GenericScraper(parser, result_folder)

    all_processed: list[pd.DataFrame] = []
    failed_urls: list[str] = []

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
            text="Failed URLs:\n" + "\n".join(failed_urls),
        )

    if not all_processed:
        logger.warning(f"[{site_name}] No data collected")
        return pd.DataFrame()

    return pd.concat(all_processed).reset_index(drop=True)


def load_url_config() -> dict:
    """Load URL configurations from JSON file."""
    with open("url_configs.json") as f:
        return json.load(f)


def _handle_reprocess(args: argparse.Namespace) -> None:
    """Handle the reprocess command."""
    path = args.file or args.folder
    results = reprocess_raw_data(
        site=args.site,
        path=path,
        output_mode=args.output,
        base_path=args.result_folder,
    )
    if results:
        logger.info(f"[{args.site}] Reprocessed {len(results)} files")
    else:
        logger.warning(f"[{args.site}] No files were reprocessed")


def _handle_scrape(args: argparse.Namespace) -> None:
    """Handle the scrape command."""
    if args.url:
        if args.scraper_name == "all":
            raise SystemExit("Error: --scraper_name is required when using --url")

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


def main() -> None:
    """Main entry point for the CLI."""
    arg_parser = argparse.ArgumentParser(description="Scrape real estate listings")
    subparsers = arg_parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape listings from sites")
    scrape_parser.add_argument("--scraper_name", default="all", help="Site name or 'all'")
    scrape_parser.add_argument("--result_folder", default="results", help="Output folder")
    scrape_parser.add_argument("--url", help="Single URL to scrape (bypasses config, prints to console)")
    scrape_parser.add_argument("--save", action="store_true", help="Save results to file when using --url")

    # Reprocess command
    reprocess_parser = subparsers.add_parser("reprocess", help="Reprocess raw data with current transforms")
    reprocess_parser.add_argument("--site", required=True, help="Site name (e.g., Suprimmo, ImotBg)")
    reprocess_parser.add_argument("--folder", help="Folder to reprocess (e.g., plovdiv/apartments)")
    reprocess_parser.add_argument("--file", help="Single raw CSV file to reprocess")
    reprocess_parser.add_argument(
        "--output",
        choices=["overwrite", "new"],
        default="overwrite",
        help="Output mode: 'overwrite' existing or create 'new' timestamped files",
    )
    reprocess_parser.add_argument("--result_folder", default="results", help="Base results folder")

    args = arg_parser.parse_args()

    if args.command == "reprocess":
        _handle_reprocess(args)
    elif args.command == "scrape":
        _handle_scrape(args)


if __name__ == "__main__":
    main()
