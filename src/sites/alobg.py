import re

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_currency,
    extract_offer_type,
    extract_property_type,
    parse_price,
)
from src.core.normalization import normalize_city, normalize_neighborhood


def extract_alo_city(location: str) -> str:
    """Extract and normalize city from location like 'Редута, София' -> 'София'"""
    if not location:
        return ""
    parts = location.split(", ")
    city = parts[-1].strip() if parts else ""
    result = normalize_city(city)
    return result.value if hasattr(result, "value") else result


def extract_alo_neighborhood(location: str) -> str:
    """Extract and normalize neighborhood from location like 'Редута, София' -> 'Редута'"""
    if not location:
        return ""
    parts = location.split(", ")
    neighborhood = parts[0].strip() if len(parts) > 1 else ""
    if not neighborhood:
        return ""
    city = extract_alo_city(location)
    result = normalize_neighborhood(neighborhood, city)
    return result.value if hasattr(result, "value") else result


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
        offer_type = Field("title", extract_offer_type)
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        city = Field("location", extract_alo_city)
        neighborhood = Field("location", extract_alo_neighborhood)
        area = Field("area_text")  # Keep as string to match model
        floor = Field("floor_text")  # Keep as string to match model
        details_url = Field("details_url", prepend_url=True)
        raw_description = Field("description")
        agency = Field("agency_name")

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

        return {
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
        }

    def extract_listings(self, soup):
        # Extract from both top listings and vip listings
        for item in soup.select("div.listtop-item, div.listvip-item"):
            listing = self._extract_listing(item)
            if listing:
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
