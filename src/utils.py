import os
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

from src.logger_setup import get_logger

logger = get_logger(__name__)


def parse_soup(page_content: str) -> BeautifulSoup:
    if not page_content:
        raise ValueError("Page content cannot be empty")
    return BeautifulSoup(page_content, "html.parser")


def get_now_for_filename() -> str:
    return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")


def get_now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def save_df_to_csv(
    df: pd.DataFrame,
    result_path: str,
    date_for_name: str,
    url_idx: int,
) -> bool:
    if df.empty:
        logger.warning(f"DataFrame is empty, not saving to {result_path}")
        return False

    os.makedirs(result_path, exist_ok=True)
    file_path = os.path.join(result_path, f"{date_for_name}_{url_idx}.csv")

    logger.info(f"Saving {df.shape[0]} rows to {file_path}")
    df.to_csv(file_path, index=False, encoding="utf-8")
    return True
