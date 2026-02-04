"""
Base extractor for site-specific data extraction.

Extractors are responsible for:
- Parsing HTML/JSON content from real estate sites
- Extracting raw fields into a unified RawListing schema
- Handling pagination
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.models import RawListing
from src.logger_setup import get_logger

logger = get_logger(__name__)


@dataclass
class SiteConfig:
    """Configuration for a scraping target site."""

    name: str
    base_url: str
    encoding: str = "utf-8"
    source_type: str = "html"  # "html" or "json"
    rate_limit_seconds: float = 1.0
    max_pages: int = 100
    page_size: int = 100
    use_cloudscraper: bool = False


class BaseExtractor(ABC):
    """
    Abstract base class for site-specific extractors.

    Each site implements its own extractor that:
    - Defines site configuration (URL, encoding, rate limits)
    - Extracts listings from HTML/JSON into RawListing objects
    - Handles site-specific pagination logic
    """

    config: SiteConfig

    # =========================================================================
    # HTML Helpers
    # =========================================================================

    def get_text(self, selector: str, element: BeautifulSoup, default: str = "") -> str:
        """Extract text content from an element using CSS selector."""
        found = element.select_one(selector)
        return found.get_text(strip=True) if found else default

    def get_href(self, selector: str, element: BeautifulSoup) -> str | None:
        """Extract href attribute from an element using CSS selector."""
        found = element.select_one(selector)
        return found.get("href") if found else None

    def get_attr(self, selector: str, attr_name: str, element: BeautifulSoup) -> str | None:
        """Extract any attribute from an element using CSS selector."""
        found = element.select_one(selector)
        return found.get(attr_name) if found else None

    # =========================================================================
    # JSON Helpers
    # =========================================================================

    def get_json_value(self, data: dict, dot_path: str, default: Any = None) -> Any:
        """
        Extract value from nested dict using dot notation path.

        Example: get_json_value(data, "price.value") returns data["price"]["value"]
        """
        for key in dot_path.split("."):
            if not isinstance(data, dict):
                return default
            data = data.get(key, {})
        return data if data != {} else default

    # =========================================================================
    # Text Extraction Helpers
    # =========================================================================

    def extract_total_floors(self, text: str) -> str:
        """Extract total floors from Bulgarian property text.

        Handles common patterns:
        - "Етажност: X" or "Етажност на сградата: X"
        - "от X етажа" or "от X ет."
        - "X-етажна сграда"
        """
        if not text:
            return ""
        if match := re.search(r"Етажност(?:\s+на\s+сградата)?:\s*(\d+)", text, re.IGNORECASE):
            return match.group(1)
        if match := re.search(r"\bот\s*(\d+)\s*(?:етаж|ет\.)", text, re.IGNORECASE):
            return match.group(1)
        if match := re.search(r"(\d+)-етажна", text, re.IGNORECASE):
            return match.group(1)
        return ""

    def extract_badges(self, element: Tag, selector: str, exclude_classes: list[str] | None = None) -> str:
        """Extract badge/label text from an element.

        Args:
            element: Parent element to search within
            selector: CSS selector for badge elements
            exclude_classes: List of CSS classes to skip (e.g., ["video-label"])

        Returns:
            Comma-separated string of badge texts
        """
        exclude_classes = exclude_classes or []
        badges = []
        for badge in element.select(selector):
            badge_classes = " ".join(badge.get("class", []))
            if any(exc in badge_classes for exc in exclude_classes):
                continue
            text = " ".join(badge.get_text(separator=" ").split())
            if text:
                badges.append(text)
        return ", ".join(badges)

    def prepend_offer_type(self, title: str, offer_type: str) -> str:
        """Prepend offer type to title if not already present."""
        if offer_type and offer_type not in title.lower():
            return f"{offer_type} {title}"
        return title

    # =========================================================================
    # URL Helpers
    # =========================================================================

    def prepend_base_url(self, path: str | None) -> str:
        """
        Prepend base URL to a relative path.

        Handles:
        - None/empty paths -> ""
        - Already absolute URLs -> return as-is
        - Protocol-relative URLs (//example.com) -> add https:
        - Relative paths -> prepend base_url
        """
        if not path:
            return ""
        if path.startswith("http"):
            return path
        if path.startswith("//"):
            return f"https:{path}"
        return f"{self.config.base_url}{path}"

    def build_page_url(self, current_url: str, page_number: int, param_name: str = "page") -> str:
        """Build URL for a specific page number.

        Handles existing page parameter replacement and adding new parameter.

        Args:
            current_url: The current page URL
            page_number: Target page number
            param_name: Query parameter name for page (default: "page")

        Returns:
            URL with page parameter set to page_number
        """
        pattern = rf"{param_name}=\d+"
        if re.search(pattern, current_url):
            return re.sub(pattern, f"{param_name}={page_number}", current_url)
        separator = "&" if "?" in current_url else "?"
        return f"{current_url}{separator}{param_name}={page_number}"

    def extract_ref_from_url(self, url: str, patterns: list[str]) -> str:
        """Extract reference number from URL using multiple patterns.

        Args:
            url: URL to extract from
            patterns: List of regex patterns with a capture group for the reference

        Returns:
            First matched reference number or empty string
        """
        if not url:
            return ""
        for pattern in patterns:
            if match := re.search(pattern, url):
                return match.group(1)
        return ""

    # =========================================================================
    # URL Building (Static)
    # =========================================================================

    @staticmethod
    def build_urls(config: dict) -> list[dict]:
        """
        Build list of URLs to scrape from site configuration.

        Default implementation returns urls list from config.
        Override in subclasses for site-specific URL building logic.

        Args:
            config: Site configuration from url_configs.json

        Returns:
            List of URL configs, each with "url" and optional "name", "folder" keys
        """
        return config.get("urls", [])

    # =========================================================================
    # Abstract Methods (must be implemented by each site)
    # =========================================================================

    @abstractmethod
    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """
        Extract listings from page content.

        Args:
            content: BeautifulSoup for HTML sites, dict for JSON sites

        Yields:
            RawListing objects with extracted data
        """
        pass

    @abstractmethod
    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """
        Get URL for the next page of results.

        Args:
            content: Current page content (BeautifulSoup or dict)
            current_url: URL of the current page
            page_number: The next page number to fetch

        Returns:
            URL for next page, or None if no more pages
        """
        pass

    # =========================================================================
    # Optional Methods (can be overridden)
    # =========================================================================

    def get_total_pages(self, content: Any) -> int:
        """
        Get total number of pages for pagination.

        Default returns max_pages from config.
        Override to extract actual page count from content.
        """
        return self.config.max_pages
