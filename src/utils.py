from typing import Any, Dict, Optional

from bs4 import BeautifulSoup, Tag

from src.logger_setup import get_logger

logger = get_logger(__name__)


def get_text_or_none(
    tag: BeautifulSoup,
    selector: tuple,
    attribute: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    try:
        element = tag.find(*selector, **(attribute or {}))
        return element.get_text(strip=True) if element else None
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
