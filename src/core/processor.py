import math
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core.extractor import BaseExtractor
from src.core.models import RawListing
from src.core.transformer import Transformer
from src.logger_setup import get_logger
from src.utils import get_now_for_filename, get_year_month_path

logger = get_logger(__name__)


def _clean_raw_value(value) -> str | None:
    """Clean a raw CSV value for RawListing construction."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return str(value) if value != int(value) else str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value) if value else None


def _clean_field_value(key: str, value) -> tuple:
    """Clean a single field value for RawListing construction.

    Returns:
        Tuple of (cleaned_value, warning_message or None)
    """
    try:
        # Handle NaN values first
        if pd.isna(value) if hasattr(pd, "isna") else (isinstance(value, float) and math.isnan(value)):
            return None, None

        if value is None:
            return None, None

        if key == "scraped_at":
            if isinstance(value, str):
                return datetime.fromisoformat(value), None
            return value, None

        if key in ("num_photos", "total_offers"):
            return int(float(value)), None

        if key == "ref_no":
            # ref_no must be string (pandas may read numeric-only values as int)
            return str(int(value)) if isinstance(value, float) else str(value), None

        if key.endswith("_text"):
            # All _text fields must be strings (pandas may read numeric-only values as float)
            return _clean_raw_value(value), None

        # Default: return value as-is if truthy, else None
        return value if value else None, None

    except (ValueError, TypeError) as e:
        return None, f"Field '{key}' could not be parsed (value={value!r}): {e}"


def _record_to_raw_listing(record: dict) -> tuple[RawListing, list[str]]:
    """Convert a CSV record dict to a RawListing object.

    Returns:
        Tuple of (RawListing, list of warning messages)
    """
    cleaned = {}
    warnings = []

    for key, value in record.items():
        cleaned_value, warning = _clean_field_value(key, value)
        cleaned[key] = cleaned_value
        if warning:
            warnings.append(warning)

    return RawListing(**cleaned), warnings


class Processor:
    """Processes raw listing files into normalized data."""

    def __init__(self, extractor: BaseExtractor, base_path: str = "results", year_month_override: str | None = None):
        self.extractor = extractor
        self.site_name = extractor.config.name
        self.base_path = Path(base_path)
        self.year_month_override = year_month_override
        self.transformer = Transformer()

    def _raw_dir(self) -> Path:
        """Get path to raw data directory."""
        year_month = self.year_month_override or get_year_month_path()
        return self.base_path / year_month / "raw" / self.site_name

    def _processed_dir(self) -> Path:
        """Get path to processed data directory."""
        year_month = self.year_month_override or get_year_month_path()
        return self.base_path / year_month / "processed" / self.site_name

    def _get_output_path(self, raw_file: Path) -> Path:
        """Get output path for a raw file."""
        rel_path = raw_file.relative_to(self._raw_dir())
        return self._processed_dir() / rel_path

    def get_unprocessed_files(self) -> list[Path]:
        """Find raw files that haven't been processed yet."""
        raw_dir = self._raw_dir()
        if not raw_dir.exists():
            return []

        unprocessed = []
        for raw_file in raw_dir.rglob("*.csv"):
            if not self._get_output_path(raw_file).exists():
                unprocessed.append(raw_file)
        return sorted(unprocessed)

    def process_file(self, raw_file: Path) -> Path | None:
        """Process a single raw file through the transformer.

        Args:
            raw_file: Path to raw CSV file

        Returns:
            Path to processed file, or None if processing failed
        """
        logger.info(f"[{self.site_name}] Processing {raw_file}")

        raw_df = pd.read_csv(raw_file)
        if raw_df.empty:
            logger.warning(f"[{self.site_name}] Empty file: {raw_file}")
            return None

        processed = []
        for record in raw_df.to_dict("records"):
            try:
                # Convert record to RawListing
                raw_listing, field_warnings = _record_to_raw_listing(record)
                # Log any field parsing warnings
                for warning in field_warnings:
                    logger.warning(f"[{self.site_name}] {warning}")
                # Transform to ListingData
                listing_data = self.transformer.transform(raw_listing)
                processed.append(listing_data.model_dump())
            except Exception as e:
                logger.warning(f"[{self.site_name}] Transform failed: {e}")

        if not processed:
            logger.warning(f"[{self.site_name}] No listings processed from {raw_file}")
            return None

        output_file = self._get_output_path(raw_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(processed).to_csv(output_file, index=False, encoding="utf-8")

        logger.info(f"[{self.site_name}] Saved {len(processed)} listings to {output_file}")
        return output_file

    def process_all_unprocessed(self) -> list[Path]:
        """Process all unprocessed raw files.

        Returns:
            List of paths to processed files
        """
        unprocessed = self.get_unprocessed_files()
        if not unprocessed:
            logger.info(f"[{self.site_name}] No unprocessed files")
            return []

        logger.info(f"[{self.site_name}] Found {len(unprocessed)} unprocessed files")
        results = []
        for raw_file in unprocessed:
            result = self.process_file(raw_file)
            if result:
                results.append(result)
        return results

    def reprocess_file(self, raw_file: Path, output_mode: str = "overwrite") -> Path | None:
        """Reprocess a file with updated transformer.

        Args:
            raw_file: Path to raw CSV file
            output_mode: "overwrite" to replace existing, "new" to create new file

        Returns:
            Path to processed file, or None if processing failed
        """
        if output_mode == "overwrite":
            return self.process_file(raw_file)

        result = self.process_file(raw_file)
        if not result:
            return None

        timestamp = get_now_for_filename()
        new_name = f"{raw_file.stem}_reprocessed_{timestamp}.csv"
        new_path = result.parent / new_name
        result.rename(new_path)
        return new_path

    def reprocess_folder(self, folder: str, output_mode: str = "overwrite") -> list[Path]:
        """Reprocess all files in a folder.

        Args:
            folder: Subfolder name within raw directory
            output_mode: "overwrite" or "new"

        Returns:
            List of paths to processed files
        """
        folder_path = self._raw_dir() / folder
        if not folder_path.exists():
            logger.error(f"[{self.site_name}] Folder not found: {folder_path}")
            return []

        results = []
        for raw_file in sorted(folder_path.glob("*.csv")):
            result = self.reprocess_file(raw_file, output_mode)
            if result:
                results.append(result)
        return results

    def reprocess_all(self, output_mode: str = "overwrite") -> list[Path]:
        """Reprocess all raw files.

        Args:
            output_mode: "overwrite" or "new"

        Returns:
            List of paths to processed files
        """
        raw_dir = self._raw_dir()
        if not raw_dir.exists():
            logger.error(f"[{self.site_name}] Directory not found: {raw_dir}")
            return []

        folders = set()
        for csv_file in raw_dir.rglob("*.csv"):
            folders.add(str(csv_file.parent.relative_to(raw_dir)))

        results = []
        for folder in sorted(folders):
            results.extend(self.reprocess_folder(folder, output_mode))
        return results
