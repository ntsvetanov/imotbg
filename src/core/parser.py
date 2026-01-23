from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterator

from bs4 import BeautifulSoup

from src.core.models import ListingData


@dataclass
class Field:
    source: str
    transform: Callable | None = None
    prepend_url: bool = False


@dataclass
class SiteConfig:
    name: str
    base_url: str
    encoding: str = "utf-8"
    source_type: str = "html"
    rate_limit_seconds: float = 1.0
    max_pages: int = 100
    page_size: int = 100


class BaseParser(ABC):
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

    def transform_listing(self, raw_listing: dict) -> ListingData:
        result = {"site": self.config.name}

        for attr_name in dir(self.Fields):
            if attr_name.startswith("_"):
                continue

            field_obj = getattr(self.Fields, attr_name)
            if not isinstance(field_obj, Field):
                continue

            raw_value = raw_listing.get(field_obj.source)
            if field_obj.transform is None:
                result[attr_name] = raw_value
            elif raw_value is not None:
                try:
                    result[attr_name] = field_obj.transform(raw_value)
                except Exception:
                    result[attr_name] = None

            if field_obj.prepend_url and result.get(attr_name):
                result[attr_name] = self._prepend_base_url(result[attr_name])

        # Map scraped_at to date_time_added if present
        if "scraped_at" in raw_listing and raw_listing["scraped_at"]:
            try:
                result["date_time_added"] = datetime.fromisoformat(raw_listing["scraped_at"])
            except (ValueError, TypeError):
                pass

        return ListingData(**result)
