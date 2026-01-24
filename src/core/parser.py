from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterator

from bs4 import BeautifulSoup

from src.core.models import ListingData
from src.logger_setup import get_logger

logger = get_logger(__name__)


@dataclass
class Field:
    """Mapping from raw data field to transformed output field."""

    source: str
    transform: Callable | None = None
    prepend_url: bool = False


@dataclass
class SiteConfig:
    """Configuration for a scraping target site."""

    name: str
    base_url: str
    encoding: str = "utf-8"
    source_type: str = "html"
    rate_limit_seconds: float = 1.0
    max_pages: int = 100
    page_size: int = 100


class BaseParser(ABC):
    """Abstract base class for site-specific parsers."""

    config: SiteConfig
    Fields: type

    @staticmethod
    def build_urls(config: dict) -> list[dict]:
        return config.get("urls", [])

    def get_text(self, selector: str, element: BeautifulSoup, default: str = "") -> str:
        found = element.select_one(selector)
        return found.get_text(strip=True) if found else default

    def get_href(self, selector: str, element: BeautifulSoup) -> str | None:
        found = element.select_one(selector)
        return found.get("href") if found else None

    def get_attr(self, selector: str, attr_name: str, element: BeautifulSoup) -> str | None:
        found = element.select_one(selector)
        return found.get(attr_name) if found else None

    def get_json_value(self, data: dict, dot_path: str, default=None):
        for key in dot_path.split("."):
            if not isinstance(data, dict):
                return default
            data = data.get(key, {})
        return data if data != {} else default

    @abstractmethod
    def extract_listings(self, content: Any) -> Iterator[dict]:
        pass

    @abstractmethod
    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        pass

    def get_total_pages(self, content: Any) -> int:
        return self.config.max_pages

    def _prepend_base_url(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("http"):
            return path
        if path.startswith("//"):
            return f"https:{path}"
        return f"{self.config.base_url}{path}"

    def _apply_transform(self, field_obj: Field, attr_name: str, raw_value: Any) -> Any:
        """Apply field transform with proper error handling."""
        if field_obj.transform is None:
            return raw_value
        if raw_value is None:
            return None
        try:
            return field_obj.transform(raw_value)
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"[{self.config.name}] Transform failed for field '{attr_name}': {e} (value: {raw_value!r})")
            return None

    def transform_listing(self, raw_listing: dict) -> ListingData:
        result: dict[str, Any] = {"site": self.config.name}

        for attr_name in dir(self.Fields):
            if attr_name.startswith("_"):
                continue

            field_obj = getattr(self.Fields, attr_name)
            if not isinstance(field_obj, Field):
                continue

            raw_value = raw_listing.get(field_obj.source)
            transformed_value = self._apply_transform(field_obj, attr_name, raw_value)

            if transformed_value is not None:
                if field_obj.prepend_url:
                    transformed_value = self._prepend_base_url(transformed_value)
                result[attr_name] = transformed_value

        if raw_listing.get("scraped_at"):
            try:
                result["date_time_added"] = datetime.fromisoformat(raw_listing["scraped_at"])
            except (ValueError, TypeError) as e:
                logger.debug(f"[{self.config.name}] Failed to parse scraped_at: {e}")

        return ListingData(**result)
