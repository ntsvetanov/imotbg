import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class BulgarianPropertiesExtractor(BaseExtractor):
    """Extractor for bulgarianproperties.bg."""

    config = SiteConfig(
        name="bulgarianproperties",
        base_url="https://www.bulgarianproperties.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.5,
        use_cloudscraper=True,
    )

    def _get_area(self, size_text: str) -> str:
        """Extract area from text like '(7,08€/м2)(13,84лв./м2)Площ: 212.00 м2Етаж: 5'."""
        if not size_text:
            return ""
        # Try "Площ: X м2" format first
        if match := re.search(r"Площ:\s*(\d+(?:[.,]\d+)?)\s*(?:кв\.?м|m2|м2)", size_text, re.IGNORECASE):
            return f"{match.group(1).replace(',', '.')} кв.м"
        # Fallback to any area format
        if match := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:кв\.?м|m2|м2)", size_text, re.IGNORECASE):
            return f"{match.group(1).replace(',', '.')} кв.м"
        return ""

    def _get_floor(self, size_text: str) -> str:
        """Extract floor from text like '(7,08€/м2)(13,84лв./м2)Площ: 212.00 м2Етаж: 5'."""
        if match := re.search(r"Етаж:\s*(\d+)", size_text or "", re.IGNORECASE):
            return match.group(1)
        return ""

    def _get_total_floors(self, size_text: str) -> str:
        """Extract total floors from text (if available)."""
        return self.extract_total_floors(size_text)

    def _get_ref_from_url(self, url: str) -> str:
        """Extract reference number from URL like '/imoti-mezoneti/imot-89171-mezonet-pod-naem.html'."""
        return self.extract_ref_from_url(url, [r"imot-(\d+)", r"/(\d+)\.html"])

    def _get_badges(self, card: Tag) -> str:
        """Extract badges from listing card (standard-label, video-label, etc.)."""
        return self.extract_badges(card, ".top-labels .label", exclude_classes=["video-label"])

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page.

        The total is shown in format: <div class="results"><span class="count">3637</span>...</div>
        """
        # Try the specific selector for span.count inside div.results first
        if count_elem := soup.select_one("div.results span.count"):
            text = count_elem.get_text(strip=True)
            if text.isdigit():
                return int(text)

        # Fallback to generic selectors
        for selector in [".results-count", ".search-results-count", ".total-results", "h1", ".page-title"]:
            if elem := soup.select_one(selector):
                text = elem.get_text(strip=True)
                if match := re.search(r"(\d[\d\s]*)\s*(?:имот|резултат|оферт)", text, re.IGNORECASE):
                    return int(match.group(1).replace(" ", ""))
        return 0

    def _get_listing_data(self, card: Tag) -> dict | None:
        """Extract data from a single listing card."""
        # Extract title and raw_link_description
        title_elem = card.select_one("a.title, .title a, .content .title")
        title = title_elem.get_text(strip=True) if title_elem else ""
        raw_link_description = title_elem.get("title", "") if title_elem else ""

        # Extract details URL
        link_elem = card.select_one("a.title, .property-item-top a.image, a[href*='/imoti/']")
        details_url = link_elem.get("href") if link_elem else None

        # Extract size text for area/floor extraction
        size_elem = card.select_one(".size, span.size")
        size_text = size_elem.get_text(strip=True) if size_elem else ""

        # Extract reference number
        ref_elem = card.select_one(".ref-no, [class*='ref']")
        ref_no = ref_elem.get_text(strip=True) if ref_elem else ""
        if not ref_no and details_url:
            ref_no = self._get_ref_from_url(details_url)

        return {
            "title": title,
            "raw_link_description": raw_link_description,
            "details_url": details_url,
            "price_text": self.get_text(
                ".regular-price, .new-price, .property-prices .regular-price, .property-prices .new-price, span.regular-price, span.new-price",
                card,
            ),
            "location": self.get_text(".location, span.location", card),
            "description": self.get_text(".list-description, .description", card),
            "area_text": self._get_area(size_text),
            "floor_text": self._get_floor(size_text),
            "total_floors_text": self._get_total_floors(size_text),
            "ref_no": ref_no,
            "agency_name": self.get_text(".broker .broker-info .name, .broker .name", card) or "Bulgarian Properties",
            "num_photos": len(card.select("img, .image img, .property-item-top img")),
            "badges": self._get_badges(card),
        }

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from bulgarianproperties.bg HTML page."""
        soup: BeautifulSoup = content
        total_offers = self._extract_total_offers(soup)
        scraped_at = datetime.now()

        for card in soup.select("div.component-property-item"):
            data = self._get_listing_data(card)

            # Combine description with badges
            description = data["description"]
            if data["badges"]:
                description = f"{data['badges']}, {description}" if description else data["badges"]

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=self.prepend_base_url(data["details_url"]) if data["details_url"] else None,
                price_text=data["price_text"],
                location_text=data["location"],
                title=data["title"],
                description=description,
                area_text=data["area_text"],
                floor_text=data["floor_text"],
                total_floors_text=data["total_floors_text"],
                agency_name=data["agency_name"],
                num_photos=data["num_photos"],
                ref_no=data["ref_no"],
                total_offers=total_offers,
                raw_link_description=data["raw_link_description"],
            )

    def get_total_pages(self, content: Any) -> int:
        """Extract total pages from pagination."""
        soup: BeautifulSoup = content
        max_page = 1
        for link in soup.select("a.page, .pagination a, a[href*='page=']"):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if match := re.search(r"page=(\d+)", href):
                max_page = max(max_page, int(match.group(1)))
            elif text.isdigit():
                max_page = max(max_page, int(text))
        return max_page if max_page > 1 else self.config.max_pages

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        soup: BeautifulSoup = content
        if not soup.select("div.component-property-item"):
            return None
        if page_number > self.get_total_pages(soup):
            return None

        return self.build_page_url(current_url, page_number)
