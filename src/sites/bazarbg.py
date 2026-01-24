import re

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_city,
    extract_currency,
    extract_offer_type,
    extract_property_type,
    parse_price,
)


def extract_location_city(location: str) -> str:
    if not location:
        return ""
    return extract_city(location.replace("гр. ", ""))


def extract_location_neighborhood(location: str) -> str:
    if not location:
        return ""
    parts = location.split(", ", 1)
    return parts[1].strip() if len(parts) > 1 else ""


class BazarBgParser(BaseParser):
    config = SiteConfig(
        name="bazarbg",
        base_url="https://bazar.bg",
        encoding="utf-8",
        rate_limit_seconds=1.5,
    )

    class Fields:
        raw_title = Field("title")
        property_type = Field("title", extract_property_type)
        offer_type = Field("title", extract_offer_type)
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        city = Field("location", extract_location_city)
        neighborhood = Field("location", extract_location_neighborhood)
        details_url = Field("details_url", prepend_url=True)
        ref_no = Field("ref_no")
        time = Field("date")

    def extract_listings(self, soup):
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

            yield {
                "title": title,
                "details_url": href,
                "ref_no": ref_no,
                "price_text": price_text,
                "location": location,
                "date": date,
            }

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
