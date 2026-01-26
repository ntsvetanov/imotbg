import re

from src.core.normalization import normalize_city, normalize_neighborhood
from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    calculate_price_per_m2,
    enum_value_or_str,
    extract_area,
    extract_currency,
    extract_floor,
    extract_offer_type,
    extract_property_type,
    is_valid_offer_type,
    parse_price,
)


def extract_location_city(location: str) -> str:
    """Extract and normalize city from location like 'гр. Пловдив, Център'."""
    if not location:
        return ""
    city = location.replace("гр. ", "").split(",")[0].strip()
    return enum_value_or_str(normalize_city(city))


def extract_location_neighborhood(location: str) -> str:
    """Extract and normalize neighborhood from location like 'гр. Пловдив, Център'."""
    if not location:
        return ""
    parts = location.split(", ", 1)
    neighborhood = parts[1].strip() if len(parts) > 1 else ""
    if not neighborhood:
        return ""
    city = extract_location_city(location)
    return enum_value_or_str(normalize_neighborhood(neighborhood, city))


def _calculate_listing_price_per_m2(raw: dict) -> str:
    """Calculate price per m2 from raw listing data."""
    price = parse_price(raw.get("price_text", ""))
    area_str = raw.get("area", "")
    if not area_str:
        # Try to extract from title
        area_str = extract_area(raw.get("title", ""))
    return calculate_price_per_m2(price, area_str)


class BazarBgParser(BaseParser):
    config = SiteConfig(
        name="bazarbg",
        base_url="https://bazar.bg",
        encoding="utf-8",
        rate_limit_seconds=1.5,
        use_cloudscraper=True,  # Bypass Cloudflare protection
    )

    class Fields:
        raw_title = Field("title")
        property_type = Field("title", extract_property_type)
        offer_type = Field("offer_type")  # Pre-normalized in extract_listings
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        city = Field("location", extract_location_city)
        neighborhood = Field("location", extract_location_neighborhood)
        details_url = Field("details_url", prepend_url=True)
        ref_no = Field("ref_no")
        time = Field("date")
        area = Field("area")
        floor = Field("floor")
        num_photos = Field("num_photos")
        total_offers = Field("total_offers")
        price_per_m2 = Field("price_per_m2")
        search_url = Field("search_url")

    def _extract_total_offers(self, soup) -> int:
        """Extract total offers count from page.

        Bazar.bg shows count like "Над 22123 обяви" in meta description.
        """
        # Try meta description first
        meta_desc = soup.select_one("meta[name='description']")
        if meta_desc:
            content = meta_desc.get("content", "")
            match = re.search(r"Над\s*([\d\s]+)\s*обяви", content)
            if match:
                return int(match.group(1).replace(" ", ""))

        # Try og:description
        og_desc = soup.select_one("meta[property='og:description']")
        if og_desc:
            content = og_desc.get("content", "")
            match = re.search(r"Над\s*([\d\s]+)\s*обяви", content)
            if match:
                return int(match.group(1).replace(" ", ""))

        return 0

    def _detect_offer_type_from_page(self, soup) -> str:
        """Detect default offer type from page URL in canonical link.

        Bazar.bg URLs contain patterns like:
        - /prodazhba-apartamenti/ for sales
        - /naemi-apartamenti/ for rentals
        """
        # Check canonical URL
        canonical = soup.select_one("link[rel='canonical']")
        if canonical:
            url = canonical.get("href", "")
            offer_type = extract_offer_type("", url)
            if is_valid_offer_type(offer_type):
                return offer_type

        # Check og:url
        og_url = soup.select_one("meta[property='og:url']")
        if og_url:
            url = og_url.get("content", "")
            offer_type = extract_offer_type("", url)
            if is_valid_offer_type(offer_type):
                return offer_type

        return ""

    def extract_listings(self, soup):
        # Extract total offers from the page (only once per page)
        total_offers = self._extract_total_offers(soup)

        # Detect default offer type from page context
        default_offer_type = self._detect_offer_type_from_page(soup)

        for item in soup.select("div.listItemContainer"):
            link = item.select_one("a.listItemLink")
            if not link:
                continue

            title = link.get("title", "")
            href = link.get("href", "")
            ref_no = link.get("data-id", "")

            price_elem = link.select_one("span.price")
            price_text = price_elem.get_text(strip=True) if price_elem else ""

            location = self.get_text("span.location", link)
            date = self.get_text("span.date", link)

            # Count photos (images in the listing card)
            photos = item.select("img.cover, img.photo, img.lazy")
            num_photos = len(photos) if photos else 0

            # Try to extract area and floor from title
            # Titles like "Продава 3-СТАЕН, 85 кв.м, 5 ет." may contain this info
            area = extract_area(title)
            floor = extract_floor(title)

            # Determine offer type: try from title first, fall back to page context
            offer_type = extract_offer_type(title, href)
            if not is_valid_offer_type(offer_type):
                offer_type = default_offer_type

            raw = {
                "title": title,
                "details_url": href,
                "ref_no": ref_no,
                "price_text": price_text,
                "location": location,
                "date": date,
                "area": area,
                "floor": floor,
                "num_photos": num_photos,
                "total_offers": total_offers,
                "offer_type": offer_type,
            }

            # Calculate price per m2
            raw["price_per_m2"] = _calculate_listing_price_per_m2(raw)

            yield raw

    def get_total_pages(self, soup) -> int:
        pagination = soup.select_one("div.paging")
        if not pagination:
            return 1
        page_links = pagination.select("a.btn.not-current")
        if not page_links:
            return 1
        last_page_text = page_links[-1].get_text(strip=True)
        match = re.search(r"\d+", last_page_text)
        return int(match.group()) if match else 1

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        if not soup.select("div.listItemContainer"):
            return None

        total = self.get_total_pages(soup)
        if page_number > total:
            return None

        if "page=" in current_url:
            return re.sub(r"page=\d+", f"page={page_number}", current_url)

        separator = "&" if "?" in current_url else "?"
        return f"{current_url}{separator}page={page_number}"
