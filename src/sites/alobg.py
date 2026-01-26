import re

from src.core.normalization import normalize_city, normalize_neighborhood
from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    calculate_price_per_m2,
    enum_value_or_str,
    extract_area,
    extract_currency,
    extract_offer_type,
    extract_property_type,
    is_valid_offer_type,
    parse_price,
)


def extract_alo_city(location: str) -> str:
    """Extract and normalize city from location like 'Редута, София' -> 'София'."""
    if not location:
        return ""
    parts = location.split(", ")
    city = parts[-1].strip() if parts else ""
    return enum_value_or_str(normalize_city(city))


def extract_alo_neighborhood(location: str) -> str:
    """Extract and normalize neighborhood from location like 'Редута, София' -> 'Редута'."""
    if not location:
        return ""
    parts = location.split(", ")
    neighborhood = parts[0].strip() if len(parts) > 1 else ""
    if not neighborhood:
        return ""
    city = extract_alo_city(location)
    return enum_value_or_str(normalize_neighborhood(neighborhood, city))


def extract_ref_from_url(url: str) -> str:
    """Extract reference number from URL.

    Handles multiple URL formats:
    - '/obiava/12345-...' -> '12345'
    - '/yujen-dvustaen-apartament-10383253' -> '10383253'
    """
    if not url:
        return ""
    # Try obiava format first
    match = re.search(r"/obiava/(\d+)", url)
    if match:
        return match.group(1)
    # Try trailing number format (common in alo.bg URLs)
    match = re.search(r"-(\d{6,})(?:\?|$|/)", url)
    if match:
        return match.group(1)
    # Try any trailing number at end of URL path
    match = re.search(r"-(\d+)$", url.split("?")[0])
    if match:
        return match.group(1)
    return ""


def _calculate_listing_price_per_m2(raw: dict) -> str:
    """Calculate price per m2 from raw listing data."""
    price = parse_price(raw.get("price_text", ""))
    area_str = extract_area(raw.get("area_text", ""))
    return calculate_price_per_m2(price, area_str)


class AloBgParser(BaseParser):
    config = SiteConfig(
        name="alobg",
        base_url="https://www.alo.bg",
        encoding="utf-8",
        rate_limit_seconds=1.5,
    )

    class Fields:
        raw_title = Field("title")
        property_type = Field("property_type_text", extract_property_type)
        offer_type = Field("offer_type")  # Pre-normalized in extract_listings
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        city = Field("location", extract_alo_city)
        neighborhood = Field("location", extract_alo_neighborhood)
        area = Field("area_text")  # Keep as string to match model
        floor = Field("floor_text")  # Keep as string to match model
        details_url = Field("details_url", prepend_url=True)
        raw_description = Field("description")
        agency = Field("agency_name")
        ref_no = Field("ref_no")
        num_photos = Field("num_photos")
        total_offers = Field("total_offers")
        price_per_m2 = Field("price_per_m2")
        search_url = Field("search_url")

    def _extract_param_value(self, item, param_name: str) -> str:
        """Extract parameter value from listing item by looking for param title."""
        for row in item.select(".ads-params-row"):
            title_elem = row.select_one(".ads-param-title")
            if title_elem and param_name in title_elem.get_text(strip=True):
                value_elem = row.select_one(".ads-params-cell .ads-params-single")
                if value_elem:
                    return value_elem.get_text(strip=True)
        # Also check multi-format params (used in VIP listings)
        for span in item.select(".ads-params-multi"):
            title_attr = span.get("title", "")
            if param_name in title_attr:
                return span.get_text(strip=True)
        return ""

    def _extract_listing(self, item) -> dict | None:
        """Extract data from a single listing item (top or vip)."""
        # Get title and URL
        title_elem = item.select_one("h3.listtop-item-title, h3.listvip-item-title")
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        # Get details URL
        link = item.select_one("a[href]")
        href = link.get("href", "") if link else ""
        if href and not href.startswith("/"):
            href = "/" + href

        # Get location from address element
        address_elem = item.select_one(".listtop-item-address i, .listvip-item-address i")
        location = address_elem.get_text(strip=True) if address_elem else ""

        # Get parameters
        price_text = self._extract_param_value(item, "Цена")
        property_type_text = self._extract_param_value(item, "Вид на имота")
        area_text = self._extract_param_value(item, "Квадратура")
        construction_type = self._extract_param_value(item, "Вид строителство")
        year_text = self._extract_param_value(item, "Година на строителство")
        floor_text = self._extract_param_value(item, "Номер на етажа")

        # Get description
        desc_elem = item.select_one(".listtop-desc, .listvip-desc")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Get agency name
        publisher_elem = item.select_one(".listtop-publisher span, .listvip-publisher span")
        agency_name = ""
        if publisher_elem:
            # First span in publisher is agency name
            spans = item.select(".listtop-publisher span, .listvip-publisher span")
            if spans:
                agency_name = spans[0].get_text(strip=True)

        # Extract reference number from URL
        ref_no = extract_ref_from_url(href)

        # Count photos
        photos = item.select("img.listtop-item-photo, img.listvip-item-photo, .gallery img")
        num_photos = len(photos) if photos else 0

        raw = {
            "title": title,
            "details_url": href,
            "location": location,
            "price_text": price_text,
            "property_type_text": property_type_text,
            "area_text": area_text,
            "construction_type": construction_type,
            "year_text": year_text,
            "floor_text": floor_text,
            "description": description,
            "agency_name": agency_name,
            "ref_no": ref_no,
            "num_photos": num_photos,
        }

        # Calculate price per m2
        raw["price_per_m2"] = _calculate_listing_price_per_m2(raw)

        return raw

    def _extract_total_offers(self, soup) -> int:
        """Extract total offers count from page.

        Alo.bg shows count like "157 обяви" or "Намерени 157 обяви" in page header.
        """
        # Try multiple selectors for different page layouts
        for selector in [
            ".search-results-count",
            ".results-count",
            ".list-count",
            "h1",  # Sometimes count is in the main heading
            ".category-list-title",
        ]:
            count_elem = soup.select_one(selector)
            if count_elem:
                text = count_elem.get_text(strip=True)
                # Match patterns like "157 обяви" or "Намерени 157"
                match = re.search(r"(\d[\d\s]*)\s*обяв", text.replace("\xa0", " "))
                if match:
                    return int(match.group(1).replace(" ", ""))
        return 0

    def _detect_offer_type_from_page(self, soup) -> str:
        """Detect default offer type from page URL embedded in page or meta tags.

        Alo.bg URLs contain patterns like:
        - /imoti-prodajbi/ for sales
        - /imoti-naemi/ for rentals
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

        # Check page title or breadcrumbs for sale/rent keywords
        title = soup.select_one("title")
        if title:
            title_text = title.get_text(strip=True).lower()
            if "продажб" in title_text or "prodajb" in title_text:
                return "продава"
            elif "наем" in title_text or "naem" in title_text:
                return "наем"

        return ""

    def extract_listings(self, soup):
        # Extract total offers from the page (only once per page)
        total_offers = self._extract_total_offers(soup)

        # Detect default offer type from page context (URL patterns in meta tags)
        default_offer_type = self._detect_offer_type_from_page(soup)

        # Extract from both top listings and vip listings
        for item in soup.select("div.listtop-item, div.listvip-item"):
            listing = self._extract_listing(item)
            if listing:
                listing["total_offers"] = total_offers

                # Determine offer_type: try from title first, fall back to page context
                title = listing.get("title", "")
                offer_type = extract_offer_type(title, "")
                if not is_valid_offer_type(offer_type):
                    offer_type = default_offer_type
                listing["offer_type"] = offer_type

                yield listing

    def get_total_pages(self, soup) -> int:
        """Extract total pages from pagination."""
        # Look for pagination - alo.bg uses div.my-paginator
        paging = soup.select_one("div.my-paginator")
        if not paging:
            # Fallback to other pagination selectors
            paging = soup.select_one("ul.pagination, div.paging")
        if not paging:
            return 1
        page_links = paging.select("a")
        max_page = 1
        for link in page_links:
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        # Check if there are any listings
        has_items = bool(soup.select("div.listtop-item, div.listvip-item"))
        if not has_items:
            return None

        total = self.get_total_pages(soup)
        if page_number > total:
            return None

        # URL format uses &page=N parameter
        if "&page=" in current_url:
            return re.sub(r"&page=\d+", f"&page={page_number}", current_url)
        elif "?page=" in current_url:
            return re.sub(r"\?page=\d+", f"?page={page_number}", current_url)
        else:
            separator = "&" if "?" in current_url else "?"
            return f"{current_url}{separator}page={page_number}"
