import re

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_city,
    extract_currency,
    extract_neighborhood,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
    extract_agency,
)


def extract_photo_count(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)\s*снимк", text)
    return int(match.group(1)) if match else None


def extract_area(info_text: str) -> str:
    """Extract area from info text like '56 кв.м, 6-ти ет.'"""
    if not info_text:
        return ""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*кв\.?\s*м", info_text)
    return match.group(1).replace(",", ".") if match else ""


def extract_floor(info_text: str) -> str:
    """Extract floor from info text like '6-ти ет. от 8' or 'ет. 3'"""
    if not info_text:
        return ""
    # Match patterns like "6-ти ет.", "ет. 3", "3 ет."
    match = re.search(r"(\d+)(?:-\w+)?\s*ет\.?|ет\.?\s*(\d+)", info_text)
    if match:
        return match.group(1) or match.group(2)
    return ""


def extract_ref_from_id(item_id: str) -> str:
    """Extract reference number from item id like 'ida123'"""
    if not item_id:
        return ""
    match = re.search(r"id[a-z]?(\d+)", item_id)
    return match.group(1) if match else ""


def calculate_price_per_m2(raw: dict) -> str:
    """Calculate price per m2 from price_text and info_text"""
    try:
        price = parse_price(raw.get("price_text", ""))
        area_str = extract_area(raw.get("info_text", ""))
        if price and area_str:
            area = float(area_str)
            if area > 0:
                return str(round(price / area, 2))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return ""


class ImotBgParser(BaseParser):
    config = SiteConfig(
        name="imotbg",
        base_url="https://www.imot.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.0,
    )

    class Fields:
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        without_dds = Field("price_text", is_without_dds)
        city = Field("location", extract_city)
        neighborhood = Field("location", extract_neighborhood)
        raw_title = Field("title")
        property_type = Field("title", extract_property_type)
        offer_type = Field("title", extract_offer_type)
        raw_description = Field("description")
        details_url = Field("details_url", prepend_url=True)
        num_photos = Field("photos_text", extract_photo_count)
        contact_info = Field("contact_info")
        agency = Field("agency_name", extract_agency)
        agency_url = Field("agency_url", prepend_url=True)
        area = Field("info_text", extract_area)
        floor = Field("info_text", extract_floor)
        ref_no = Field("ref_no")
        total_offers = Field("total_offers")
        price_per_m2 = Field("price_per_m2")

    def _extract_contact_from_description(self, description_text: str) -> str:
        if "тел.:" in description_text:
            return description_text.split("тел.:")[-1].strip()
        return ""

    def _extract_title_and_location(self, item) -> tuple[str, str]:
        title_elem = item.select_one("a.title")
        if not title_elem:
            return "", ""

        location_elem = title_elem.select_one("location")
        location = location_elem.get_text(strip=True) if location_elem else ""

        if location_elem:
            location_elem.decompose()
        title = title_elem.get_text(strip=True)

        return title, location

    def _extract_total_offers(self, soup) -> int:
        """Extract total offers count from page like 'Обяви 1-24 от общо 1234'"""
        # Look for the count in pagination or header
        count_elem = soup.select_one("span.pageNumbersInfo")
        if count_elem:
            text = count_elem.get_text(strip=True)
            match = re.search(r"от\s*общо\s*(\d+)", text)
            if match:
                return int(match.group(1))
        return 0

    def extract_listings(self, soup):
        # Extract total offers from the page (only once per page)
        total_offers = self._extract_total_offers(soup)

        for item in soup.select("div.item"):
            title, location = self._extract_title_and_location(item)
            description = self.get_text("div.info", item)
            info_text = self.get_text("div.info", item)
            photos_link = item.select_one("a.photos")
            photos_text = photos_link.get_text(strip=True) if photos_link else ""

            # Extract ref_no from item id attribute
            item_id = item.get("id", "")
            ref_no = extract_ref_from_id(item_id)

            raw = {
                "price_text": self.get_text("div.price div", item),
                "title": title,
                "location": location,
                "description": description,
                "info_text": info_text,
                "details_url": self.get_href("a.title", item),
                "photos_text": photos_text,
                "contact_info": self._extract_contact_from_description(description),
                "agency_name": self.get_text("div.seller div.name", item),
                "agency_url": self.get_href("div.seller a", item),
                "ref_no": ref_no,
                "total_offers": total_offers,
            }

            # Calculate price per m2
            raw["price_per_m2"] = calculate_price_per_m2(raw)

            yield raw

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        has_items = bool(soup.select("div.item"))
        if not has_items:
            return None

        base_url = re.sub(r"/p-\d+", "", current_url)

        if "?" in base_url:
            path, query = base_url.split("?", 1)
            return f"{path}/p-{page_number}?{query}"

        return f"{base_url}/p-{page_number}"
