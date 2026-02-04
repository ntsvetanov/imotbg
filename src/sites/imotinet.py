import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class ImotiNetExtractor(BaseExtractor):
    """Extractor for imoti.net."""

    config = SiteConfig(
        name="imotinet",
        base_url="https://www.imoti.net",
        encoding="utf-8",
        rate_limit_seconds=1.0,
    )

    def _extract_params(self, listing: BeautifulSoup) -> tuple[str, str]:
        """Extract floor and price_per_m2 from parameters list."""
        params = listing.select("ul.parameters li")
        floor = params[0].get_text(strip=True) if params else ""
        price_per_m2 = params[1].get_text(strip=True) if len(params) > 1 else ""
        return floor, price_per_m2

    def _extract_description(self, listing: BeautifulSoup) -> str:
        """Extract description from listing."""
        description_p = listing.select("p")
        return description_p[1].get_text(strip=True) if len(description_p) > 1 else ""

    def _extract_area_from_title(self, title: str) -> str:
        """Extract area from title like 'Тристаен, 85 кв.м'."""
        parts = title.split(",") if title else []
        return parts[1].strip() if len(parts) > 1 else ""

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page like '/999+ имота/'."""
        elem = soup.select_one("span#number-of-estates")
        if elem:
            text = elem.get_text(strip=True)
            # Handle "999+" case
            if "999+" in text:
                return 999
            # Extract number from text like "/123 имота/"
            match = re.search(r"(\d+)", text)
            if match:
                return int(match.group(1))
        return 0

    def _extract_ref_no(self, url: str) -> str:
        """Extract reference number from URL like '/bg/obiava/.../6196041/'."""
        if not url:
            return ""
        # Match the last number in the URL path (before optional query string)
        match = re.search(r"/(\d+)/?(?:\?|$)", url)
        return match.group(1) if match else ""

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from imoti.net HTML page."""
        soup: BeautifulSoup = content
        scraped_at = datetime.now()
        total_offers = self._extract_total_offers(soup)

        for listing in soup.select("li.clearfix"):
            title = self.get_text("h3", listing)
            floor_text, _ = self._extract_params(listing)
            area_text = self._extract_area_from_title(title)
            details_url = self.prepend_base_url(self.get_href("a.box-link", listing))

            # Get number of photos
            photos_text = self.get_text("span.pic-video-info-number", listing)
            num_photos = None
            if photos_text and photos_text.isdigit():
                num_photos = int(photos_text)

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=details_url,
                price_text=self.get_text("strong.price", listing),
                location_text=self.get_text("span.location", listing),
                title=title,
                description=self._extract_description(listing),
                area_text=area_text,
                floor_text=floor_text,
                agency_name=self.get_text("span.re-offer-type", listing),
                num_photos=num_photos,
                ref_no=self._extract_ref_no(details_url),
                total_offers=total_offers,
            )

    def get_total_pages(self, content: Any) -> int:
        """Get total pages from pagination."""
        soup: BeautifulSoup = content
        last_page = soup.select_one("nav.paginator a.last-page")
        return int(last_page.text.strip()) if last_page else 1

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        soup: BeautifulSoup = content
        total = self.get_total_pages(soup)
        if page_number > total:
            return None
        return current_url.replace("page=1", f"page={page_number}")
