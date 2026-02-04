import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class AloBgExtractor(BaseExtractor):
    """Extractor for alo.bg."""

    config = SiteConfig(
        name="alobg",
        base_url="https://www.alo.bg",
        encoding="utf-8",
        rate_limit_seconds=1.5,
    )

    def _get_ref_from_url(self, url: str) -> str:
        """Extract reference number from URL.

        Handles multiple URL formats:
        - '/obiava/12345-...' -> '12345'
        - '/yujen-dvustaen-apartament-10383253' -> '10383253'
        """
        return self.extract_ref_from_url(
            url,
            [
                r"/obiava/(\d+)",
                r"-(\d{6,})(?:\?|$|/)",
                r"-(\d+)$",
            ],
        )

    def _get_param_value(self, card: Tag, param_name: str) -> str:
        """Extract parameter value from listing card by looking for param title."""
        for row in card.select(".ads-params-row"):
            title_elem = row.select_one(".ads-param-title")
            if title_elem and param_name in title_elem.get_text(strip=True):
                if value_elem := row.select_one(".ads-params-cell .ads-params-single"):
                    return value_elem.get_text(strip=True)
        # Also check multi-format params (used in VIP listings)
        for span in card.select(".ads-params-multi"):
            if param_name in span.get("title", ""):
                return span.get_text(strip=True)
        return ""

    def _get_title(self, card: Tag) -> str:
        """Extract title from listing card."""
        if title_elem := card.select_one("h3.listtop-item-title, h3.listvip-item-title"):
            return title_elem.get_text(strip=True)
        return ""

    def _get_details_url(self, card: Tag) -> str:
        """Extract details URL from listing card."""
        if link := card.select_one("a[href]"):
            href = link.get("href", "")
            return href if href.startswith("/") else f"/{href}" if href else ""
        return ""

    def _get_raw_link_description(self, card: Tag) -> str:
        """Extract raw_link_description from link or h3 title attribute."""
        if link := card.select_one("a[href]"):
            if title := link.get("title", ""):
                return title
            if h3 := link.select_one("h3"):
                return h3.get("title", "")
        return ""

    def _get_location(self, card: Tag) -> str:
        """Extract location from address element."""
        if address_elem := card.select_one(".listtop-item-address i, .listvip-item-address i"):
            return address_elem.get_text(strip=True)
        return ""

    def _get_description(self, card: Tag) -> str:
        """Extract description from listing card."""
        if desc_elem := card.select_one(".listtop-desc, .listvip-desc"):
            return desc_elem.get_text(strip=True)
        return ""

    def _get_agency_name(self, card: Tag) -> str:
        """Extract agency name from listing card."""
        if spans := card.select(".listtop-publisher span, .listvip-publisher span"):
            return spans[0].get_text(strip=True)
        return ""

    def _get_num_photos(self, card: Tag) -> int:
        """Count photos in listing card."""
        # Look for main listing images, excluding icon images (like top/vip badges)
        photos = card.select(
            "img.listtop-image-img, img.listvip-image-img, img.listtop-item-photo, img.listvip-item-photo, .gallery img"
        )
        return len(photos) if photos else 0

    def _get_listing_data(self, card: Tag) -> dict | None:
        """Extract data from a single listing card."""
        title = self._get_title(card)
        if not title:
            return None

        details_url = self._get_details_url(card)
        description = self._get_description(card)

        # Extract total_floors from parameter or description
        total_floors_text = self._get_param_value(card, "Етажност")
        if not total_floors_text:
            total_floors_text = self.extract_total_floors(description)

        return {
            "title": title,
            "details_url": details_url,
            "location": self._get_location(card),
            "price_text": self._get_param_value(card, "Цена"),
            "area_text": self._get_param_value(card, "Квадратура"),
            "floor_text": self._get_param_value(card, "Номер на етажа"),
            "total_floors_text": total_floors_text,
            "description": description,
            "agency_name": self._get_agency_name(card),
            "ref_no": self._get_ref_from_url(details_url),
            "num_photos": self._get_num_photos(card),
            "raw_link_description": self._get_raw_link_description(card),
        }

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page."""
        for selector in [
            ".obiavicnt",
            ".search-results-count",
            ".results-count",
            ".list-count",
            ".category-list-title",
        ]:
            if count_elem := soup.select_one(selector):
                text = count_elem.get_text(strip=True)
                if match := re.search(r"(\d[\d\s]*)\s*обяв", text.replace("\xa0", " ")):
                    return int(match.group(1).replace(" ", ""))
        return 0

    def _detect_offer_type(self, soup: BeautifulSoup) -> str:
        """Detect offer type from page URL in meta tags."""
        # Check canonical URL
        if canonical := soup.select_one("link[rel='canonical']"):
            url = canonical.get("href", "").lower()
            if "prodajb" in url or "prodazh" in url:
                return "продава"
            if "naem" in url:
                return "наем"

        # Check page title
        if title := soup.select_one("title"):
            title_text = title.get_text(strip=True).lower()
            if "продажб" in title_text or "prodajb" in title_text:
                return "продава"
            if "наем" in title_text or "naem" in title_text:
                return "наем"

        return ""

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from alo.bg HTML page."""
        soup: BeautifulSoup = content
        total_offers = self._extract_total_offers(soup)
        default_offer_type = self._detect_offer_type(soup)
        scraped_at = datetime.now()

        for card in soup.select("div.listtop-item, div.listvip-item"):
            if not (data := self._get_listing_data(card)):
                continue

            # Build title with offer type for transformer
            title = self.prepend_offer_type(data["title"], default_offer_type)

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=self.prepend_base_url(data["details_url"]),
                price_text=data["price_text"],
                location_text=data["location"],
                title=title,
                description=data["description"],
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
        paging = soup.select_one("div.my-paginator") or soup.select_one("ul.pagination, div.paging")
        if not paging:
            return 1
        max_page = 1
        for link in paging.select("a"):
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        soup: BeautifulSoup = content
        if not soup.select("div.listtop-item, div.listvip-item, div.listtop-params"):
            return None
        if page_number > self.get_total_pages(soup):
            return None

        return self.build_page_url(current_url, page_number)
