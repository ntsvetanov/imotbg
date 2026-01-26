import argparse
import json
from pathlib import Path

from src.core.downloader import Downloader
from src.core.processor import Processor
from src.logger_setup import get_logger
from src.sites import SITE_PARSERS, get_parser

logger = get_logger(__name__)


def load_url_config() -> dict:
    with open("url_configs.json") as f:
        return json.load(f)


def download_site(site_name: str, result_folder: str) -> int:
    parser = get_parser(site_name)
    downloader = Downloader(parser, result_folder)

    url_config = load_url_config()
    site_config = url_config.get(site_name, {})
    urls = parser.build_urls(site_config)

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
    parser = get_parser(site_name)
    processor = Processor(parser, result_folder)

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
    parser = get_parser(site_name)

    if file_path:
        processor = Processor(parser, result_folder)
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
                processor = Processor(parser, result_folder, year_month_override=year_month)
                if folder:
                    results = processor.reprocess_folder(folder, output_mode)
                else:
                    results = processor.reprocess_all(output_mode)
                total_results.extend(results)
        logger.info(f"[{site_name}] Reprocessed {len(total_results)} files (all history)")
        return len(total_results)

    processor = Processor(parser, result_folder)
    if folder:
        results = processor.reprocess_folder(folder, output_mode)
    else:
        results = processor.reprocess_all(output_mode)

    logger.info(f"[{site_name}] Reprocessed {len(results)} files")
    return len(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Real estate listings scraper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # download
    dl = subparsers.add_parser("download", help="Download raw data")
    dl.add_argument("--site", default="all")
    dl.add_argument("--result_folder", default="results")

    # process
    pr = subparsers.add_parser("process", help="Process raw data")
    pr.add_argument("--site", default="all")
    pr.add_argument("--file")
    pr.add_argument("--result_folder", default="results")

    # scrape = download + process
    sc = subparsers.add_parser("scrape", help="Download and process")
    sc.add_argument("--site", default="all")
    sc.add_argument("--result_folder", default="results")

    # reprocess
    rp = subparsers.add_parser("reprocess", help="Reprocess with updated transforms")
    rp.add_argument("--site", required=True)
    rp.add_argument("--folder")
    rp.add_argument("--file")
    rp.add_argument("--all", action="store_true", help="Reprocess all historical data")
    rp.add_argument("--output", choices=["overwrite", "new"], default="overwrite")
    rp.add_argument("--result_folder", default="results")

    args = parser.parse_args()
    sites = list(SITE_PARSERS.keys()) if args.site == "all" else [args.site]

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


if __name__ == "__main__":
    main()
