import re
from datetime import datetime
from typing import Any, Iterator

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class HomesBgExtractor(BaseExtractor):
    """Extractor for homes.bg - uses JSON API."""

    config = SiteConfig(
        name="homesbg",
        base_url="https://www.homes.bg",
        source_type="json",
        rate_limit_seconds=2.0,
        max_pages=30,
        page_size=100,
    )

    def _parse_location(self, location: str) -> tuple[str, str]:
        """Parse location string like 'Лозенец, София' -> (city, neighborhood)."""
        if not location:
            return "", ""
        parts = location.split(",")
        neighborhood = parts[0].strip()
        city = parts[1].strip() if len(parts) > 1 else ""
        return city, neighborhood

    def _determine_offer_type(self, search_criteria: dict) -> str:
        """Determine offer type from search criteria typeId."""
        type_id = search_criteria.get("typeId", "").lower()
        # Map typeId to offer type text for transformer
        if type_id in ("apartmentsell", "housesell", "landsell", "landagro", "sell"):
            return "продава"
        elif type_id in ("apartmentrent", "houserent", "rent"):
            return "наем"
        return type_id  # Return raw value for transformer to handle

    def _extract_area_from_title(self, title: str | None) -> str | None:
        """
        Extract area from title like 'Двустаен, 62m²' -> '62 m²'.

        Also handles: '62m2', '62 m2', '62м²', '62 кв.м'
        """
        if not title:
            return None

        # Pattern to match area in title
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|м²|кв\.?\s*м)", title, re.IGNORECASE)
        if match:
            return f"{match.group(1)} кв.м"
        return None

    def _extract_floor_from_url(self, url: str | None) -> str | None:
        """
        Extract floor from URL if present.

        URL pattern: /offer/apartament-za-prodazhba/dvustaen-62m2-et-3-sofiya-oborishte/as1660040
        """
        if not url:
            return None

        match = re.search(r"-et-(\d+)-", url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_total_offers(self, data: dict) -> int | None:
        """Extract total offers count from JSON response."""
        # Try 'totalCount' field
        total = data.get("totalCount")
        if total is not None:
            return int(total)

        # Try 'total' field
        total = data.get("total")
        if total is not None:
            return int(total)

        # Try 'count' field
        total = data.get("count")
        if total is not None:
            return int(total)

        return None

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        """Extract listings from homes.bg JSON response."""
        data: dict = content
        search_criteria = data.get("searchCriteria", {})
        offer_type = self._determine_offer_type(search_criteria)
        scraped_at = datetime.now()
        total_offers = self._extract_total_offers(data)

        for item in data.get("result", []):
            location = item.get("location", "")
            city, neighborhood = self._parse_location(location)
            price_data = item.get("price", {})

            # Build price text for transformer
            price_value = price_data.get("value")
            currency = price_data.get("currency", "")
            price_text = ""
            if price_value:
                currency_symbol = "€" if currency.upper() == "EUR" else currency
                price_text = f"{price_value} {currency_symbol}"

            # Build location text for transformer
            location_text = f"{city}, {neighborhood}" if city and neighborhood else location

            # Extract area from title
            title = item.get("title", "")
            area_text = self._extract_area_from_title(title)

            # Build full title with offer type prefix
            if offer_type and title:
                full_title = f"{offer_type} {title}"
            elif offer_type:
                full_title = offer_type
            elif title:
                full_title = title
            else:
                full_title = None

            # Extract floor from URL
            view_href = item.get("viewHref")
            floor_text = self._extract_floor_from_url(view_href)

            # Count photos (can be list of strings or list of dicts)
            photos = item.get("photos", [])
            num_photos = len(photos) if photos is not None else 0

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=self.prepend_base_url(view_href),
                price_text=price_text,
                location_text=location_text,
                title=full_title,
                description=item.get("description"),
                area_text=area_text,
                floor_text=floor_text,
                num_photos=num_photos,
                ref_no=str(item.get("id", "")),
                total_offers=total_offers,
            )

    def get_total_pages(self, content: Any) -> int:
        """Get total pages from JSON response."""
        return self.config.max_pages

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        """Get URL for next page of results."""
        data: dict = content
        if not data.get("hasMoreItems", False):
            return None
        start_index = (page_number - 1) * self.config.page_size
        stop_index = page_number * self.config.page_size
        base_url = current_url.split("&startIndex")[0]
        return f"{base_url}&startIndex={start_index}&stopIndex={stop_index}"
