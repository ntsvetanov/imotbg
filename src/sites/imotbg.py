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
)


def extract_photo_count(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)\s*снимк", text)
    return int(match.group(1)) if match else None


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
        agency_name = Field("agency_name")
        agency_url = Field("agency_url", prepend_url=True)

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

    def extract_listings(self, soup):
        for item in soup.select("div.item"):
            title, location = self._extract_title_and_location(item)
            description = self.get_text("div.info", item)
            photos_link = item.select_one("a.photos")
            photos_text = photos_link.get_text(strip=True) if photos_link else ""

            yield {
                "price_text": self.get_text("div.price div", item),
                "title": title,
                "location": location,
                "description": description,
                "details_url": self.get_href("a.title", item),
                "photos_text": photos_text,
                "contact_info": self._extract_contact_from_description(description),
                "agency_name": self.get_text("div.seller div.name", item),
                "agency_url": self.get_href("div.seller a", item),
            }

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        has_items = bool(soup.select("div.item"))
        if not has_items:
            return None

        base_url = re.sub(r"/p-\d+", "", current_url)

        if "?" in base_url:
            path, query = base_url.split("?", 1)
            return f"{path}/p-{page_number}?{query}"

        return f"{base_url}/p-{page_number}"
