import math
from pathlib import Path

import pandas as pd

from src.core.normalization import clear_unknown_values, log_unknown_values_summary
from src.core.parser import BaseParser
from src.logger_setup import get_logger
from src.utils import get_now_for_filename, get_year_month_path

logger = get_logger(__name__)


def clean_raw_record(record: dict) -> dict:
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, float):
            cleaned[key] = None if math.isnan(value) else str(value)
        elif isinstance(value, int):
            cleaned[key] = str(value)
        else:
            cleaned[key] = value
    return cleaned


class Processor:
    def __init__(self, parser: BaseParser, base_path: str = "results"):
        self.parser = parser
        self.site_name = parser.config.name
        self.base_path = Path(base_path)

    def _raw_dir(self) -> Path:
        year_month = get_year_month_path()
        return self.base_path / year_month / "raw" / self.site_name

    def _processed_dir(self) -> Path:
        year_month = get_year_month_path()
        return self.base_path / year_month / "processed" / self.site_name

    def _get_output_path(self, raw_file: Path) -> Path:
        rel_path = raw_file.relative_to(self._raw_dir())
        return self._processed_dir() / rel_path

    def get_unprocessed_files(self) -> list[Path]:
        raw_dir = self._raw_dir()
        if not raw_dir.exists():
            return []

        unprocessed = []
        for raw_file in raw_dir.rglob("*.csv"):
            if not self._get_output_path(raw_file).exists():
                unprocessed.append(raw_file)
        return sorted(unprocessed)

    def process_file(self, raw_file: Path) -> Path | None:
        logger.info(f"[{self.site_name}] Processing {raw_file}")
        clear_unknown_values()

        raw_df = pd.read_csv(raw_file)
        if raw_df.empty:
            logger.warning(f"[{self.site_name}] Empty file: {raw_file}")
            return None

        processed = []
        for record in raw_df.to_dict("records"):
            try:
                cleaned = clean_raw_record(record)
                transformed = self.parser.transform_listing(cleaned).model_dump()
                processed.append(transformed)
            except Exception as e:
                logger.warning(f"[{self.site_name}] Transform failed: {e}")

        if not processed:
            logger.warning(f"[{self.site_name}] No listings processed from {raw_file}")
            return None

        output_file = self._get_output_path(raw_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(processed).to_csv(output_file, index=False, encoding="utf-8")

        log_unknown_values_summary()
        logger.info(f"[{self.site_name}] Saved {len(processed)} listings to {output_file}")
        return output_file

    def process_all_unprocessed(self) -> list[Path]:
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
