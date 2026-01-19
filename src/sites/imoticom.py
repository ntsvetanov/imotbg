import re

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_currency,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
)


def extract_city(location: str) -> str | None:
    if not location:
        return None
    parts = location.split(",")
    return parts[0].strip() if parts else None


def extract_neighborhood(location: str) -> str | None:
    if not location:
        return None
    parts = location.split(",")
    return parts[1].strip() if len(parts) > 1 else None


def extract_area(location_info: str) -> str | None:
    if not location_info:
        return None
    match = re.search(r"(\d+)\s*кв\.м", location_info)
    return f"{match.group(1)} кв.м" if match else None


class ImotiComParser(BaseParser):
    config = SiteConfig(
        name="imoticom",
        base_url="https://www.imoti.com",
        encoding="utf-8",
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
        details_url = Field("details_url")
        contact_info = Field("contact_info")
        area = Field("location_info", extract_area)

    def _extract_location(self, item) -> str:
        location_div = item.select_one("div.location")
        if not location_div:
            return ""
        full_text = location_div.get_text(separator="\n", strip=True)
        lines = full_text.split("\n")
        return lines[0].strip() if lines else ""

    def _extract_location_info(self, item) -> str:
        location_div = item.select_one("div.location")
        if not location_div:
            return ""
        return location_div.get_text(separator="\n", strip=True)

    def extract_listings(self, soup):
        list_container = soup.select_one("div.list")
        if not list_container:
            return

        for item in list_container.select("div.item"):
            title = self.get_text("span.type", item)
            price_text = self.get_text("span.price", item)
            location = self._extract_location(item)
            location_info = self._extract_location_info(item)

            info_div = item.select_one("div.info")
            description = ""
            if info_div:
                for child in info_div.children:
                    if isinstance(child, str):
                        text = child.strip()
                        if text and "кв.м" not in text:
                            description = text
                            break

            details_url = self.get_href("a[href*='/obiava/']", item)

            contact_info = self.get_text("div.phones", item)
            if contact_info.startswith("тел.:"):
                contact_info = contact_info[5:].strip()

            yield {
                "price_text": price_text,
                "title": title,
                "location": location,
                "location_info": location_info,
                "description": description,
                "details_url": details_url,
                "contact_info": contact_info,
            }

    def get_total_pages(self, soup) -> int:
        last_link = soup.select_one("a.big[href*='page-']")
        if last_link:
            for link in soup.select("a.big[href*='page-']"):
                if "Последна" in link.get_text():
                    href = link.get("href", "")
                    match = re.search(r"page-(\d+)", href)
                    if match:
                        return int(match.group(1))
        return self.config.max_pages

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        total = self.get_total_pages(soup)
        if page_number > total:
            return None

        if not soup.select("div.item"):
            return None

        base_url = re.sub(r"/page-\d+", "", current_url)

        if "?" in base_url:
            path, query = base_url.split("?", 1)
            return f"{path}/page-{page_number}?{query}"

        return f"{base_url}/page-{page_number}"
