import os
import re
import shutil
from pathlib import Path

# Configuration
RESULTS_DIR = Path("results")
DATA_TYPES = ["raw", "processed"]
DRY_RUN = False  # Set to False to actually move files
# Pattern to extract year and month from filename (e.g., 2026_01_24_18_22_34_0)
DATE_PATTERN = re.compile(r"^(\d{4})_(\d{2})_\d{2}_")


def extract_year_month(filename: str) -> tuple[str, str] | None:
    """Extract year and month from filename like 2026_01_24_18_22_34_0"""
    match = DATE_PATTERN.match(filename)
    return (match.group(1), match.group(2)) if match else None


def reorganize_files():
    moved_count = 0
    skipped_count = 0
    for data_type in DATA_TYPES:
        data_type_path = RESULTS_DIR / data_type

        if not data_type_path.exists():
            print(f"Skipping {data_type_path} - does not exist")
            continue
        # Walk through site/city/type structure
        for root, dirs, files in os.walk(data_type_path):
            root_path = Path(root)

            for filename in files:
                result = extract_year_month(filename)

                if not result:
                    print(f"Skipping {filename} - cannot extract year/month")
                    skipped_count += 1
                    continue

                year, month = result
                # Get relative path after data_type (e.g., alobg/sofia/apartments)
                relative_path = root_path.relative_to(data_type_path)

                # Build new path: results/YEAR/MONTH/data_type/site/city/type/
                new_dir = RESULTS_DIR / year / month / data_type / relative_path

                old_file = root_path / filename
                new_file = new_dir / filename
                if DRY_RUN:
                    print(f"[DRY RUN] Would move:\n  {old_file}\n  -> {new_file}")
                else:
                    new_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_file), str(new_file))
                    print(f"Moved: {old_file} -> {new_file}")

                moved_count += 1
    print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Summary: {moved_count} files moved, {skipped_count} skipped")


if __name__ == "__main__":
    reorganize_files()
