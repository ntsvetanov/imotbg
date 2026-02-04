import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class ImotBgExtractor(BaseExtractor):
    """Extractor for imot.bg - one of the largest Bulgarian real estate sites."""

    config = SiteConfig(
        name="imotbg",
        base_url="https://www.imot.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.0,
        use_cloudscraper=True,
    )

    def _extract_photo_count(self, text: str) -> int | None:
        """Extract photo count from text like '5 снимки'."""
        if not text:
            return None
        match = re.search(r"(\d+)\s*снимк", text)
        return int(match.group(1)) if match else None

    def _extract_ref_from_id(self, item_id: str) -> str:
        """Extract reference number from item id like 'ida123'."""
        if not item_id:
            return ""
        match = re.search(r"id[a-z]?(\d+)", item_id)
        return match.group(1) if match else ""

    def _extract_contact_from_description(self, description_text: str) -> str:
        """Extract contact info from description text."""
        if "тел.:" in description_text:
            return description_text.split("тел.:")[-1].strip()
        return ""

    def _extract_total_floors_from_description(self, text: str | None) -> str | None:
        """
        Extract total floors from description text.

        Handles patterns like:
        - "8-ми ет. от 8" -> "8"
        - "3-ти етаж от 8" -> "8"
        - "2-ри еt. от 7" -> "7"
        - "на 3-тi етаж от 8 в панелн" -> "8"
        """
        if not text:
            return None

        # Pattern: "X-ти/ми/ри ет./етаж от Y"
        match = re.search(r"\d+(?:-\w+)?\s*(?:ет\.?|етаж)\s*от\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _extract_title_and_location(self, item: BeautifulSoup) -> tuple[str, str]:
        """Extract title and location from listing item."""
        title_elem = item.select_one("a.title")
        if not title_elem:
            return "", ""

        location_elem = title_elem.select_one("location")
        location = location_elem.get_text(strip=True) if location_elem else ""

        if location_elem:
            location_elem.decompose()
        title = title_elem.get_text(strip=True)

        return title, location

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page like '1 - 40 от общо 53 обяви'."""
        # Try div.SearchInfoLine first (new format)
        count_elem = soup.select_one("div.SearchInfoLine")
        if count_elem:
            text = count_elem.get_text(strip=True)
            match = re.search(r"от\s*общо\s*(\d+)", text)
            if match:
                return int(match.group(1))

        # Fallback to span.pageNumbersInfo (old format)
        count_elem = soup.select_one("span.pageNumbersInfo")
        if count_elem:
            text = count_elem.get_text(strip=True)
            match = re.search(r"от\s*общо\s*(\d+)", text)
            if match:
                return int(match.group(1))
        return 0

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from imot.bg HTML page."""
        soup: BeautifulSoup = content
        total_offers = self._extract_total_offers(soup)
        scraped_at = datetime.now()

        for item in soup.select("div.item"):
            title, location = self._extract_title_and_location(item)
            description = self.get_text("div.info", item)
            photos_link = item.select_one("a.photos")
            photos_text = photos_link.get_text(strip=True) if photos_link else ""

            # Extract ref_no from item id attribute
            item_id = item.get("id", "")
            ref_no = self._extract_ref_from_id(item_id)

            # Extract details URL
            details_url = self.get_href("a.title", item)

            # Extract total floors from description
            total_floors = self._extract_total_floors_from_description(description)

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=self.prepend_base_url(details_url),
                price_text=self.get_text("div.price div", item),
                location_text=location,
                title=title,
                description=description,
                area_text=description,  # Area is extracted from description
                floor_text=description,  # Floor is extracted from description
                total_floors_text=total_floors,
                agency_name=self.get_text("div.seller div.name", item),
                agency_url=self.prepend_base_url(self.get_href("div.seller a", item)),
                num_photos=self._extract_photo_count(photos_text),
                ref_no=ref_no,
                total_offers=total_offers,
            )

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        soup: BeautifulSoup = content
        has_items = bool(soup.select("div.item"))
        if not has_items:
            return None

        base_url = re.sub(r"/p-\d+", "", current_url)

        if "?" in base_url:
            path, query = base_url.split("?", 1)
            return f"{path}/p-{page_number}?{query}"

        return f"{base_url}/p-{page_number}"
