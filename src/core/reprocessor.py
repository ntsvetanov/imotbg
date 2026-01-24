import math
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.parser import BaseParser
from src.logger_setup import get_logger
from src.sites import get_parser
from src.utils import get_now_for_filename

logger = get_logger(__name__)


def _clean_raw_record(record: dict) -> dict:
    """
    Clean a raw record loaded from CSV to handle type coercion issues.

    Pandas reads CSV and:
    - Converts empty strings to NaN (float)
    - Converts numeric-looking strings to floats/ints

    We need to convert these back to appropriate types for the parser.
    """
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, float):
            if math.isnan(value):
                cleaned[key] = None
            else:
                # Convert floats back to string (pandas may have coerced string columns)
                cleaned[key] = str(value)
        elif isinstance(value, int):
            # Convert integers to string (ref_no, etc. may be read as int)
            cleaned[key] = str(value)
        else:
            cleaned[key] = value
    return cleaned


class Reprocessor:
    """Reprocesses raw scraped data using site-specific parsers."""

    def __init__(self, parser: BaseParser):
        self.parser = parser
        self.site_name = parser.config.name

    def reprocess_file(
        self,
        raw_file: Path,
        output_dir: Path,
        output_mode: str = "overwrite",
    ) -> Path | None:
        """
        Reprocess a single raw CSV file.

        Args:
            raw_file: Path to the raw CSV file
            output_dir: Directory to save processed output
            output_mode: "overwrite" to replace, "new" to create timestamped file

        Returns:
            Path to the created processed file, or None if no data
        """
        logger.info(f"[{self.site_name}] Reprocessing {raw_file}")

        raw_df = pd.read_csv(raw_file)
        if raw_df.empty:
            logger.warning(f"[{self.site_name}] Empty file: {raw_file}")
            return None

        raw_listings = raw_df.to_dict("records")
        processed_listings = []

        for raw in raw_listings:
            try:
                cleaned_raw = _clean_raw_record(raw)
                processed = self.parser.transform_listing(cleaned_raw).model_dump()
                processed_listings.append(processed)
            except Exception as e:
                logger.warning(f"[{self.site_name}] Failed to transform listing: {e}")
                continue

        if not processed_listings:
            logger.warning(f"[{self.site_name}] No listings processed from {raw_file}")
            return None

        processed_df = pd.DataFrame(processed_listings)

        os.makedirs(output_dir, exist_ok=True)

        if output_mode == "overwrite":
            output_file = output_dir / raw_file.name
        else:
            timestamp = get_now_for_filename()
            stem = raw_file.stem
            output_file = output_dir / f"{stem}_reprocessed_{timestamp}.csv"

        processed_df.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(f"[{self.site_name}] Saved {len(processed_df)} rows to {output_file}")

        return output_file

    def reprocess_folder(
        self,
        folder: str,
        base_path: str = "results",
        output_mode: str = "overwrite",
    ) -> list[Path]:
        """
        Reprocess all raw files in a folder.

        Args:
            folder: Subfolder path like "plovdiv/apartments"
            base_path: Base results directory
            output_mode: "overwrite" or "new"

        Returns:
            List of created processed file paths
        """
        raw_dir = Path(base_path) / "raw" / self.site_name / folder
        output_dir = Path(base_path) / "processed" / self.site_name / folder

        if not raw_dir.exists():
            logger.error(f"[{self.site_name}] Raw directory not found: {raw_dir}")
            return []

        raw_files = sorted(raw_dir.glob("*.csv"))
        if not raw_files:
            logger.warning(f"[{self.site_name}] No CSV files in {raw_dir}")
            return []

        logger.info(f"[{self.site_name}] Found {len(raw_files)} files in {raw_dir}")

        output_files = []
        for raw_file in raw_files:
            result = self.reprocess_file(raw_file, output_dir, output_mode)
            if result:
                output_files.append(result)

        return output_files

    def reprocess_site(
        self,
        base_path: str = "results",
        output_mode: str = "overwrite",
    ) -> list[Path]:
        """
        Reprocess all raw data for the site.

        Args:
            base_path: Base results directory
            output_mode: "overwrite" or "new"

        Returns:
            List of created processed file paths
        """
        raw_site_dir = Path(base_path) / "raw" / self.site_name

        if not raw_site_dir.exists():
            logger.error(f"[{self.site_name}] Site directory not found: {raw_site_dir}")
            return []

        # Find all folders containing CSV files
        folders = set()
        for csv_file in raw_site_dir.rglob("*.csv"):
            relative_folder = csv_file.parent.relative_to(raw_site_dir)
            folders.add(str(relative_folder))

        if not folders:
            logger.warning(f"[{self.site_name}] No CSV files found in {raw_site_dir}")
            return []

        logger.info(f"[{self.site_name}] Found {len(folders)} folders to reprocess")

        output_files = []
        for folder in sorted(folders):
            results = self.reprocess_folder(folder, base_path, output_mode)
            output_files.extend(results)

        return output_files


def reprocess_raw_data(
    site: str,
    path: str | None = None,
    output_mode: str = "overwrite",
    base_path: str = "results",
) -> list[Path]:
    """
    Main entry point for reprocessing raw data.

    Args:
        site: Site name (e.g., "Suprimmo", "ImotBg")
        path: Optional - file path, folder path, or None for entire site
        output_mode: "overwrite" to replace existing, "new" for timestamped files
        base_path: Base results directory (default: "results")

    Returns:
        List of created processed file paths

    Examples:
        # Reprocess entire site
        reprocess_raw_data("Suprimmo")

        # Reprocess a folder
        reprocess_raw_data("Suprimmo", "plovdiv/apartments")

        # Reprocess a single file
        reprocess_raw_data("Suprimmo", "results/raw/Suprimmo/plovdiv/2026_01_23.csv")

        # Create new timestamped files instead of overwriting
        reprocess_raw_data("Suprimmo", output_mode="new")
    """
    if output_mode not in ("overwrite", "new"):
        raise ValueError(f"Invalid output_mode: {output_mode}. Must be 'overwrite' or 'new'")

    parser = get_parser(site)
    reprocessor = Reprocessor(parser)

    # Determine what to reprocess
    if path is None:
        # Entire site
        logger.info(f"[{site}] Reprocessing entire site")
        return reprocessor.reprocess_site(base_path, output_mode)

    path_obj = Path(path)

    # Check if it's a file path
    if path_obj.exists() and path_obj.is_file():
        # Single file - determine output directory from file location
        # Assume structure: results/raw/{site}/{folder}/file.csv
        try:
            rel_path = path_obj.relative_to(Path(base_path) / "raw" / reprocessor.site_name)
            folder = str(rel_path.parent)
            output_dir = Path(base_path) / "processed" / reprocessor.site_name / folder
        except ValueError:
            # File is not in expected location, output to same directory
            output_dir = path_obj.parent

        result = reprocessor.reprocess_file(path_obj, output_dir, output_mode)
        return [result] if result else []

    # Treat as folder path
    return reprocessor.reprocess_folder(path, base_path, output_mode)
