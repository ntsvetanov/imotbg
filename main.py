"""
Main entry point for the real estate scraper.

Commands:
- download: Download raw data from configured sites
- process: Transform raw data into normalized format
- scrape: Download and process in one step
- reprocess: Reprocess existing raw data with updated transformer
- fetch: Fetch a single URL and output to console/file
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.downloader import Downloader
from src.core.processor import Processor
from src.core.transformer import Transformer
from src.infrastructure.clients.http_client import CloudscraperHttpClient, HttpClient
from src.logger_setup import get_logger
from src.sites import SITE_EXTRACTORS, get_extractor
from src.utils import parse_soup

logger = get_logger(__name__)


def load_url_config() -> dict:
    """Load URL configurations from JSON file."""
    with open("url_configs.json") as f:
        return json.load(f)


def download_site(site_name: str, result_folder: str) -> int:
    """Download listings from a site.

    Args:
        site_name: Name of the site to download
        result_folder: Base folder for results

    Returns:
        Number of successful downloads
    """
    extractor = get_extractor(site_name)
    downloader = Downloader(extractor, result_folder)

    url_config = load_url_config()
    site_config = url_config.get(site_name, {})
    urls = extractor.build_urls(site_config)

    if not urls:
        logger.warning(f"[{site_name}] No URLs configured")
        return 0

    success_count = 0
    for idx, url_cfg in enumerate(urls):
        try:
            logger.info(f"[{site_name}] Downloading {idx + 1}/{len(urls)}")
            result = downloader.download(url_cfg["url"], url_cfg.get("folder"), idx)
            if result:
                success_count += 1
        except Exception as e:
            logger.error(f"[{site_name}] Download failed: {e}", exc_info=True)

    logger.info(f"[{site_name}] Downloaded {success_count}/{len(urls)}")
    return success_count


def process_site(site_name: str, result_folder: str, file_path: str | None = None) -> int:
    """Process raw data for a site.

    Args:
        site_name: Name of the site to process
        result_folder: Base folder for results
        file_path: Optional specific file to process

    Returns:
        Number of files processed
    """
    extractor = get_extractor(site_name)
    processor = Processor(extractor, result_folder)

    if file_path:
        result = processor.process_file(Path(file_path))
        return 1 if result else 0

    results = processor.process_all_unprocessed()
    logger.info(f"[{site_name}] Processed {len(results)} files")
    return len(results)


def reprocess_site(
    site_name: str,
    result_folder: str,
    folder: str | None = None,
    file_path: str | None = None,
    output_mode: str = "overwrite",
    all_history: bool = False,
) -> int:
    """Reprocess raw data with updated transformer.

    Args:
        site_name: Name of the site to reprocess
        result_folder: Base folder for results
        folder: Optional subfolder to reprocess
        file_path: Optional specific file to reprocess
        output_mode: "overwrite" or "new"
        all_history: Process all historical data

    Returns:
        Number of files reprocessed
    """
    extractor = get_extractor(site_name)

    if file_path:
        processor = Processor(extractor, result_folder)
        result = processor.reprocess_file(Path(file_path), output_mode)
        return 1 if result else 0

    if all_history:
        # Reprocess all historical data across all year/month folders
        base_path = Path(result_folder)
        total_results = []
        for year_dir in sorted(base_path.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue
                year_month = f"{year_dir.name}/{month_dir.name}"
                processor = Processor(extractor, result_folder, year_month_override=year_month)
                if folder:
                    results = processor.reprocess_folder(folder, output_mode)
                else:
                    results = processor.reprocess_all(output_mode)
                total_results.extend(results)
        logger.info(f"[{site_name}] Reprocessed {len(total_results)} files (all history)")
        return len(total_results)

    processor = Processor(extractor, result_folder)
    if folder:
        results = processor.reprocess_folder(folder, output_mode)
    else:
        results = processor.reprocess_all(output_mode)

    logger.info(f"[{site_name}] Reprocessed {len(results)} files")
    return len(results)


def fetch_url(
    site_name: str,
    url: str,
    save: bool = False,
    output_path: str | None = None,
    result_folder: str = "results",
    max_pages: int | None = None,
    full: bool = False,
) -> int:
    """Fetch a single URL and output results to console.

    Args:
        site_name: Name of the site extractor to use
        url: URL to fetch
        save: Whether to also save results to CSV
        output_path: Custom output file path (default: auto-generated)
        result_folder: Base folder for auto-generated output
        max_pages: Maximum number of pages to fetch (default: all)
        full: Show all columns in console output

    Returns:
        Number of listings fetched
    """
    extractor = get_extractor(site_name)
    config = extractor.config
    transformer = Transformer()

    # Create HTTP client
    if config.use_cloudscraper:
        http_client = CloudscraperHttpClient(timeout=60, max_retries=3, retry_delay=3.0)
    else:
        http_client = HttpClient(timeout=60, max_retries=3, retry_delay=3.0)

    # Fetch and parse content
    raw_listings = []
    current_url = url
    page_number = 1

    if config.source_type == "json":
        content = http_client.fetch_json(current_url)
    else:
        html = http_client.fetch(current_url, config.encoding)
        content = parse_soup(html)

    total_pages = extractor.get_total_pages(content)
    # Limit pages if specified
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)
    logger.info(f"[{site_name}] Fetching URL, total_pages={total_pages}")

    while current_url and page_number <= total_pages:
        if page_number > 1:
            if config.source_type == "json":
                content = http_client.fetch_json(current_url)
            else:
                html = http_client.fetch(current_url, config.encoding)
                content = parse_soup(html)

        for listing in extractor.extract_listings(content):
            listing.search_url = url
            raw_listings.append(listing)

        logger.info(f"[{site_name}] Page {page_number}/{total_pages}, total={len(raw_listings)}")

        page_number += 1
        current_url = extractor.get_next_page_url(content, current_url, page_number)
        if current_url:
            time.sleep(config.rate_limit_seconds)

    if not raw_listings:
        print(f"No listings found for {site_name} at {url}")
        return 0

    # Transform all listings
    transformed = transformer.transform_batch(raw_listings)

    # Create DataFrame for display
    df = pd.DataFrame([listing.model_dump() for listing in transformed])

    # Display columns for console output
    if full:
        display_cols = list(df.columns)
    else:
        display_cols = [
            "price",
            "original_currency",
            "city",
            "neighborhood",
            "property_type",
            "area",
            "floor",
            "details_url",
        ]
        # Only include columns that exist
        display_cols = [c for c in display_cols if c in df.columns]

    print(f"\nFetched {len(transformed)} listings from {site_name}:\n")
    with pd.option_context("display.max_columns", None, "display.width", None):
        print(df[display_cols].to_string(index=False))

    # Save if requested
    if save:
        if output_path:
            file_path = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            file_path = Path(result_folder) / f"fetch_{site_name}_{timestamp}.csv"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(file_path, index=False, encoding="utf-8")
        print(f"\nSaved to: {file_path}")

    return len(transformed)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Real estate listings scraper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # download
    download_parser = subparsers.add_parser("download", help="Download raw data")
    download_parser.add_argument("--site", default="all")
    download_parser.add_argument("--result_folder", default="results")

    # process
    process_parser = subparsers.add_parser("process", help="Process raw data")
    process_parser.add_argument("--site", default="all")
    process_parser.add_argument("--file")
    process_parser.add_argument("--result_folder", default="results")

    # scrape = download + process
    scrape_parser = subparsers.add_parser("scrape", help="Download and process")
    scrape_parser.add_argument("--site", default="all")
    scrape_parser.add_argument("--result_folder", default="results")

    # reprocess
    reprocess_parser = subparsers.add_parser("reprocess", help="Reprocess with updated transformer")
    reprocess_parser.add_argument("--site", required=True)
    reprocess_parser.add_argument("--folder")
    reprocess_parser.add_argument("--file")
    reprocess_parser.add_argument("--all", action="store_true", help="Reprocess all historical data")
    reprocess_parser.add_argument("--output", choices=["overwrite", "new"], default="overwrite")
    reprocess_parser.add_argument("--result_folder", default="results")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch URL and output to console")
    fetch_parser.add_argument("--site", required=True, help="Site extractor to use")
    fetch_parser.add_argument("--url", required=True, help="URL to fetch")
    fetch_parser.add_argument("--pages", type=int, help="Max pages to fetch (default: all)")
    fetch_parser.add_argument("--full", action="store_true", help="Show all columns in output")
    fetch_parser.add_argument("--save", action="store_true", help="Also save results to CSV file")
    fetch_parser.add_argument("--output", help="Output file path (default: auto-generated)")
    fetch_parser.add_argument("--result_folder", default="results")

    args = parser.parse_args()
    sites = list(SITE_EXTRACTORS.keys()) if getattr(args, "site", "all") == "all" else [args.site]

    if args.command == "download":
        for site in sites:
            download_site(site, args.result_folder)

    elif args.command == "process":
        for site in sites:
            process_site(site, args.result_folder, getattr(args, "file", None))

    elif args.command == "scrape":
        for site in sites:
            download_site(site, args.result_folder)
            process_site(site, args.result_folder)

    elif args.command == "reprocess":
        reprocess_site(
            args.site,
            args.result_folder,
            folder=args.folder,
            file_path=args.file,
            output_mode=args.output,
            all_history=getattr(args, "all", False),
        )

    elif args.command == "fetch":
        fetch_url(
            args.site,
            args.url,
            save=args.save,
            output_path=args.output,
            result_folder=args.result_folder,
            max_pages=args.pages,
            full=args.full,
        )


if __name__ == "__main__":
    main()
