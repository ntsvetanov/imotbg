import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class ImotiComExtractor(BaseExtractor):
    """Extractor for imoti.com."""

    config = SiteConfig(
        name="imoticom",
        base_url="https://www.imoti.com",
        encoding="utf-8",
        rate_limit_seconds=1.0,
        use_cloudscraper=True,
    )

    def _get_area(self, location_info: str) -> str:
        """Extract area from location info like '85 кв.м, ет. 3'."""
        if match := re.search(r"(\d+)\s*кв\.м", location_info):
            return f"{match.group(1)} кв.м"
        return ""

    def _get_floor(self, text: str) -> str:
        """Extract floor from text like 'ет. 3', 'етаж 3', or '6-ти ет.'."""
        if not text:
            return ""
        # Pattern 1: "ет. 3" or "етаж 3"
        if match := re.search(r"(?:ет\.|етаж)\s*(\d+)", text, re.IGNORECASE):
            return match.group(1)
        # Pattern 2: "6-ти ет." or "3-ти етаж" (Bulgarian ordinal suffix)
        if match := re.search(r"(\d+)-(?:ти|ви|ри|ми|ия)\s*(?:ет\.?|етаж)", text, re.IGNORECASE):
            return match.group(1)
        return ""

    def _get_ref_from_url(self, url: str) -> str:
        """Extract reference number from URL like /obiava/23458881/..."""
        return self.extract_ref_from_url(url, [r"/obiava/(\d+)/"])

    def _get_total_floors(self, text: str) -> str:
        """Extract total floors from text (if available)."""
        return self.extract_total_floors(text)

    def _get_location(self, card: Tag) -> str:
        """Extract first line of location (city, neighborhood)."""
        if location_div := card.select_one("div.location"):
            full_text = location_div.get_text(separator="\n", strip=True)
            lines = full_text.split("\n")
            return lines[0].strip() if lines else ""
        return ""

    def _get_location_info(self, card: Tag) -> str:
        """Extract full location info (includes area, floor)."""
        if location_div := card.select_one("div.location"):
            return location_div.get_text(separator="\n", strip=True)
        return ""

    def _get_description(self, card: Tag) -> str:
        """Extract description text from info div."""
        if info_div := card.select_one("div.info"):
            for child in info_div.children:
                if isinstance(child, str):
                    text = child.strip()
                    if text and "кв.м" not in text:
                        return text
        return ""

    def _get_raw_link_description(self, card: Tag) -> str:
        """Extract raw_link_description from div.photo alt attribute."""
        if photo_div := card.select_one("div.photo"):
            return photo_div.get("alt", "")
        return ""

    def _get_num_photos(self, card: Tag) -> int:
        """Count number of photos."""
        return 1 if card.select_one("div.photo img") else 0

    def _get_agency_name(self, card: Tag) -> str:
        """Extract agency name from description text."""
        if not (info_div := card.select_one("div.info")):
            return ""

        full_text = info_div.get_text(strip=True)
        agency_patterns = [
            r"Агенция\s+(?:за\s+недвижими\s+имоти\s+)?([A-Za-zА-Яа-я\s]+?)(?:\s+(?:предлага|представя|има|с\s+удоволствие))",
            r"([A-Za-z\s]+(?:Estate|Properties|Estates|Real Estate|Имоти|Пропърти)s?)",
        ]

        for pattern in agency_patterns:
            if match := re.search(pattern, full_text, re.IGNORECASE):
                agency_name = match.group(1).strip()
                agency_name = re.sub(r"\s+(предлага|представя|има|с)$", "", agency_name)
                if len(agency_name) > 3:
                    return agency_name
        return ""

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page like '1 - 20 от общо 2000+ обяви'."""
        page_info = soup.find(string=re.compile(r"от общо"))
        if page_info and (parent := page_info.parent):
            text = parent.get_text()
            if match := re.search(r"от общо\s*(\d+)", text.replace("+", "")):
                return int(match.group(1))
        return 0

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from imoti.com HTML page."""
        soup: BeautifulSoup = content
        list_container = soup.select_one("div.list")
        if not list_container:
            return

        total_offers = self._extract_total_offers(soup)
        scraped_at = datetime.now()

        for card in list_container.select("div.item"):
            title = self.get_text("span.type", card)
            details_url = self.get_href("a[href*='/obiava/']", card)
            location_info = self._get_location_info(card)
            description = self._get_description(card)

            # Extract floor - try location_info first, then fall back to description
            floor_text = self._get_floor(location_info)
            if not floor_text:
                floor_text = self._get_floor(description)

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=details_url,
                price_text=self.get_text("span.price", card),
                location_text=self._get_location(card),
                title=title,
                description=description,
                area_text=self._get_area(location_info),
                floor_text=floor_text,
                total_floors_text=self._get_total_floors(description),
                agency_name=self._get_agency_name(card),
                num_photos=self._get_num_photos(card),
                ref_no=self._get_ref_from_url(details_url) if details_url else "",
                total_offers=total_offers,
                raw_link_description=self._get_raw_link_description(card),
            )

    def get_total_pages(self, content: Any) -> int:
        """Get total pages from pagination."""
        soup: BeautifulSoup = content
        for link in soup.select("a.big[href*='page-']"):
            if "Последна" in link.get_text():
                if match := re.search(r"page-(\d+)", link.get("href", "")):
                    return int(match.group(1))
        return self.config.max_pages

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        soup: BeautifulSoup = content
        if page_number > self.get_total_pages(soup) or not soup.select("div.item"):
            return None

        base_url = re.sub(r"/page-\d+", "", current_url)
        if "?" in base_url:
            path, query = base_url.split("?", 1)
            return f"{path}/page-{page_number}?{query}"
        return f"{base_url}/page-{page_number}"
