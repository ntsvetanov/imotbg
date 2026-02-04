import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class BazarBgExtractor(BaseExtractor):
    """Extractor for bazar.bg."""

    config = SiteConfig(
        name="bazarbg",
        base_url="https://bazar.bg",
        encoding="utf-8",
        rate_limit_seconds=1.5,
        use_cloudscraper=True,
    )

    def _get_area(self, text: str) -> str:
        """Extract area from text like 'Продава 3-СТАЕН, 85 кв.м, 5 ет.' or description."""
        if match := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:кв\.?\s*)?м", text or ""):
            return match.group(0)
        return ""

    def _get_floor(self, text: str) -> str:
        """Extract floor from text like 'Продава 3-СТАЕН, 85 кв.м, 5 ет.' or description."""
        if match := re.search(r"(\d+)\s*ет\.?", text or ""):
            return match.group(1)
        return ""

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page meta description."""
        for selector in ["meta[name='description']", "meta[property='og:description']"]:
            if meta := soup.select_one(selector):
                content = meta.get("content", "")
                if match := re.search(r"Над\s*([\d\s]+)\s*обяви", content):
                    return int(match.group(1).replace(" ", ""))
        return 0

    def _detect_offer_type(self, soup: BeautifulSoup) -> str:
        """Detect offer type from page URL in canonical link or og:url."""
        for selector in ["link[rel='canonical']", "meta[property='og:url']"]:
            if elem := soup.select_one(selector):
                url = (elem.get("href") or elem.get("content", "")).lower()
                if "prodazhba" in url or "prodajba" in url:
                    return "продава"
                if "naem" in url:
                    return "наем"
        return ""

    def _get_listing_data_v1(self, card: Tag) -> dict | None:
        """Extract data from thumbnail view format (listItemContainer)."""
        if not (link := card.select_one("a.listItemLink")):
            return None

        title = link.get("title", "")
        return {
            "title": title,
            "raw_link_description": title,
            "description": "",
            "href": link.get("href", ""),
            "ref_no": link.get("data-id", ""),
            "price_text": self.get_text("span.price", link),
            "location": self.get_text("span.location", link),
            "area_text": self._get_area(title),
            "floor_text": self._get_floor(title),
            "total_floors_text": self.extract_total_floors(title),
            "num_photos": len(card.select("img.cover, img.photo, img.lazy")),
        }

    def _get_listing_data_v2(self, card: Tag) -> dict | None:
        """Extract data from list view format (list-result with div.description)."""
        # Find the main link - try various selectors
        # Priority: title link > photo link
        link = card.select_one("div.details div.title > a, div.title > a[href*='obiava'], a.photo[href*='obiava']")
        if not link:
            # Try finding any link with obiava in href
            link = card.select_one("a[href*='obiava']")
        if not link:
            return None

        # Get title from link text, title attribute, or img alt
        title = link.get_text(strip=True)
        if not title:
            title = link.get("title", "")
        if not title:
            img = card.select_one("a.photo img, div.picture img")
            if img:
                title = img.get("alt", "")

        href = link.get("href", "")
        ref_no = link.get("data-id", "")

        # Extract description
        description = self.get_text("div.description", card)

        # Extract price
        price_text = self.get_text("div.price", card)

        # Extract location
        location = self.get_text("div.location, div.date-location .location", card)

        # Try to get area and floor from title first, then from description
        area_text = self._get_area(title)
        floor_text = self._get_floor(title)
        total_floors_text = self.extract_total_floors(title)

        # Fallback to description if not found in title
        if not area_text and description:
            area_text = self._get_area(description)
        if not floor_text and description:
            floor_text = self._get_floor(description)
        if not total_floors_text and description:
            total_floors_text = self.extract_total_floors(description)

        return {
            "title": title,
            "raw_link_description": link.get("title", "") or title,
            "description": description,
            "href": href,
            "ref_no": ref_no,
            "price_text": price_text,
            "location": location,
            "area_text": area_text,
            "floor_text": floor_text,
            "total_floors_text": total_floors_text,
            "num_photos": len(card.select("div.picture img, a.image img, a.photo img")),
        }

    def _get_listing_data(self, card: Tag) -> dict | None:
        """Extract data from a single listing card (supports both formats)."""
        # Try v1 format first (thumbnail view)
        if card.select_one("a.listItemLink"):
            return self._get_listing_data_v1(card)
        # Try v2 format (list view with description)
        return self._get_listing_data_v2(card)

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from bazar.bg HTML page."""
        soup: BeautifulSoup = content
        total_offers = self._extract_total_offers(soup)
        default_offer_type = self._detect_offer_type(soup)
        scraped_at = datetime.now()

        # Support both listing formats
        cards = soup.select("div.listItemContainer, div.list-result")

        for card in cards:
            if not (data := self._get_listing_data(card)):
                continue

            # Build title with offer type for transformer
            title = self.prepend_offer_type(data["title"], default_offer_type)

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=self.prepend_base_url(data["href"]),
                price_text=data["price_text"],
                location_text=data["location"],
                title=title,
                description=data.get("description", ""),
                area_text=data["area_text"],
                floor_text=data["floor_text"],
                total_floors_text=data["total_floors_text"],
                num_photos=data["num_photos"],
                ref_no=data["ref_no"],
                total_offers=total_offers,
                raw_link_description=data["raw_link_description"],
            )

    def get_total_pages(self, content: Any) -> int:
        """Get total pages from pagination."""
        soup: BeautifulSoup = content
        if not (pagination := soup.select_one("div.paging")):
            return 1
        if not (page_links := pagination.select("a.btn.not-current")):
            return 1
        last_page_text = page_links[-1].get_text(strip=True)
        if match := re.search(r"\d+", last_page_text):
            return int(match.group())
        return 1

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        soup: BeautifulSoup = content
        if not soup.select("div.listItemContainer, div.list-result"):
            return None
        if page_number > self.get_total_pages(soup):
            return None

        return self.build_page_url(current_url, page_number)
