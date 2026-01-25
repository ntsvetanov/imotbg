import re

from src.core.normalization import normalize_city, normalize_neighborhood
from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_currency,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
)


def extract_city_from_location(location: str) -> str:
    """Extract city from location string like 'гр. София, Лозенец'"""
    if not location:
        return ""
    parts = location.split(",")
    city = parts[0].strip()
    # Remove prefixes
    prefixes = ["гр. ", "град ", "с. "]
    for prefix in prefixes:
        if city.startswith(prefix):
            city = city[len(prefix) :]
    result = normalize_city(city)
    return result.value if hasattr(result, "value") else result


def extract_neighborhood_from_location(location: str) -> str:
    """Extract neighborhood from location string"""
    if not location:
        return ""
    parts = location.split(",")
    neighborhood = parts[1].strip() if len(parts) > 1 else ""
    if not neighborhood:
        return ""
    # Get city for context
    city = extract_city_from_location(location)
    result = normalize_neighborhood(neighborhood, city)
    return result.value if hasattr(result, "value") else result


def extract_area(size_text: str) -> str:
    """Extract area from text like '(7,08€/м2)(13,84лв./м2)Площ: 212.00 м2Етаж: 5'"""
    if not size_text:
        return ""
    # Look for "Площ: X м2" pattern
    match = re.search(r"Площ:\s*(\d+(?:[.,]\d+)?)\s*(?:кв\.?м|m2|м2)", size_text, re.IGNORECASE)
    if match:
        return match.group(1).replace(",", ".")
    # Fallback to simpler pattern
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:кв\.?м|m2|м2)", size_text, re.IGNORECASE)
    if match:
        return match.group(1).replace(",", ".")
    return ""


def extract_ref_no_from_url(url: str) -> str:
    """Extract reference number from URL like '/imoti-mezoneti/imot-89171-mezonet-pod-naem.html'"""
    if not url:
        return ""
    # Try to match imot-XXXXX pattern
    match = re.search(r"imot-(\d+)", url, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback to /XXXXX.html pattern
    match = re.search(r"/(\d+)\.html", url)
    if match:
        return match.group(1)
    return ""


def extract_price_per_m2(size_text: str) -> str:
    """Extract price per m2 from text like '(7,08€/м2)(13,84лв./м2)Площ: 212.00 м2'"""
    if not size_text:
        return ""
    # Look for EUR price per m2 first
    match = re.search(r"\((\d+(?:[.,]\d+)?)\s*€/м2\)", size_text)
    if match:
        return match.group(1).replace(",", ".")
    # Fallback to BGN price per m2
    match = re.search(r"\((\d+(?:[.,]\d+)?)\s*лв\.?/м2\)", size_text)
    if match:
        return match.group(1).replace(",", ".")
    return ""


def extract_floor(size_text: str) -> str:
    """Extract floor from text like '(7,08€/м2)(13,84лв./м2)Площ: 212.00 м2Етаж: 5'"""
    if not size_text:
        return ""
    match = re.search(r"Етаж:\s*(\d+)", size_text, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


class BulgarianPropertiesParser(BaseParser):
    config = SiteConfig(
        name="bulgarianproperties",
        base_url="https://www.bulgarianproperties.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.5,
        use_cloudscraper=True,  # Bypass Cloudflare protection
    )

    class Fields:
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        without_dds = Field("price_text", is_without_dds)
        city = Field("location", extract_city_from_location)
        neighborhood = Field("location", extract_neighborhood_from_location)
        raw_title = Field("title")
        # Use URL for property_type and offer_type extraction (more reliable)
        property_type = Field("details_url", lambda url: extract_property_type("", url))
        offer_type = Field("details_url", lambda url: extract_offer_type("", url))
        raw_description = Field("description")
        details_url = Field("details_url", prepend_url=True)
        area = Field("size_text", extract_area)
        ref_no = Field("details_url", extract_ref_no_from_url)
        agency = Field("agency_name")
        search_url = Field("search_url")
        price_per_m2 = Field("size_text", extract_price_per_m2)
        floor = Field("size_text", extract_floor)

    def extract_listings(self, soup):
        # Find all property items - looking for component-property-item class
        for item in soup.select("div.component-property-item"):
            # Extract title
            title_elem = item.select_one("a.title, .title a, .content .title")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract details URL
            details_url = None
            link_elem = item.select_one("a.title, .property-item-top a.image, a[href*='/imoti/']")
            if link_elem:
                details_url = link_elem.get("href")

            # Extract price
            price_elem = item.select_one(
                ".regular-price, .new-price, .property-prices .regular-price, "
                ".property-prices .new-price, span.regular-price, span.new-price"
            )
            price_text = price_elem.get_text(strip=True) if price_elem else ""

            # Extract location
            location_elem = item.select_one(".location, span.location")
            location = location_elem.get_text(strip=True) if location_elem else ""

            # Extract size/area
            size_elem = item.select_one(".size, span.size")
            size_text = size_elem.get_text(strip=True) if size_elem else ""

            # Extract description
            desc_elem = item.select_one(".list-description, .description")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Extract reference number
            ref_elem = item.select_one(".ref-no, [class*='ref']")
            ref_no = ref_elem.get_text(strip=True) if ref_elem else ""
            if not ref_no and details_url:
                # Try to extract from URL
                url_match = re.search(r"/(\d+)\.html", details_url or "")
                if url_match:
                    ref_no = url_match.group(1)

            # Extract broker/agency info
            broker_elem = item.select_one(".broker .broker-info .name, .broker .name")
            agency_name = broker_elem.get_text(strip=True) if broker_elem else "Bulgarian Properties"

            yield {
                "price_text": price_text,
                "title": title,
                "location": location,
                "size_text": size_text,
                "description": description,
                "details_url": details_url,
                "ref_no": ref_no,
                "agency_name": agency_name,
            }

    def get_total_pages(self, soup) -> int:
        """Extract total pages from pagination"""
        # Look for pagination links
        pagination = soup.select("a.page, .pagination a, a[href*='page=']")
        max_page = 1
        for link in pagination:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            # Try to extract page number from href
            match = re.search(r"page=(\d+)", href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)
            # Try to extract from text if it's a number
            elif text.isdigit():
                max_page = max(max_page, int(text))
        return max_page if max_page > 1 else self.config.max_pages

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        # Check if there are any listings on current page
        has_items = bool(soup.select("div.component-property-item"))
        if not has_items:
            return None

        total = self.get_total_pages(soup)
        if page_number > total:
            return None

        # Handle URL pagination
        # The site uses &page=N format
        if "page=" in current_url:
            # Replace existing page parameter
            return re.sub(r"page=\d+", f"page={page_number}", current_url)
        else:
            # Add page parameter
            separator = "&" if "?" in current_url else "?"
            return f"{current_url}{separator}page={page_number}"
