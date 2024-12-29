import os
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from src.logger_setup import get_logger

logger = get_logger(__name__)


def get_text_or_none(
    tag: BeautifulSoup,
    selector: tuple,
    attribute: Optional[Dict[str, Any]] = None,
    strip: bool = True,
) -> Optional[str]:
    try:
        element = tag.find(*selector, **(attribute or {}))
        return element.get_text(strip=strip) if element else None
    except Exception as e:
        logger.warning(f"Error getting text from {selector}: {e}")
        return None


def get_tag_text_or_none(tag: Tag, selector: tuple) -> Optional[str]:
    return get_text_or_none(tag, selector)


def get_tag_href_or_none(tag: Tag, class_name: str) -> Optional[str]:
    element = tag.find("a", class_=class_name)
    return element.get("href") if element else None


def parse_soup(page_content: str) -> BeautifulSoup:
    if not page_content:
        raise ValueError("Page content cannot be empty.")
    return BeautifulSoup(page_content, "html.parser")


def get_now_for_filename():
    date = datetime.now()
    formatted_date = date.strftime("%Y_%m_%d_%H_%M_%S")
    return formatted_date


def save_raw_csv(raw_path_prefix, df):
    formatted_date = get_now_for_filename()

    print(f"Saving raw data to {raw_path_prefix}")
    if not os.path.exists(raw_path_prefix):
        os.makedirs(raw_path_prefix)

    result_file_name = os.path.join(raw_path_prefix, f"{formatted_date}.csv")

    df.to_csv(result_file_name, index=False, encoding="utf-8")


def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
