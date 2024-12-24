from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

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
