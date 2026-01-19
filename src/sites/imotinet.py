from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_city,
    extract_currency,
    extract_neighborhood,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
    to_int_safe,
)


class ImotiNetParser(BaseParser):
    config = SiteConfig(
        name="imotinet",
        base_url="https://www.imoti.net",
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
        details_url = Field("details_url", prepend_url=True)
        num_photos = Field("num_photos", to_int_safe)
        agency = Field("agency")
        floor = Field("floor")
        price_per_m2 = Field("price_per_m2")
        area = Field("area")

    def _extract_params(self, listing) -> tuple[str, str]:
        params = listing.select("ul.parameters li")
        floor = params[0].get_text(strip=True) if params else ""
        price_per_m2 = params[1].get_text(strip=True) if len(params) > 1 else ""
        return floor, price_per_m2

    def _extract_description(self, listing) -> str:
        description_p = listing.select("p")
        return description_p[1].get_text(strip=True) if len(description_p) > 1 else ""

    def _extract_area_from_title(self, title: str) -> str:
        parts = title.split(",") if title else []
        return parts[1].strip() if len(parts) > 1 else ""

    def extract_listings(self, soup):
        for listing in soup.select("li.clearfix"):
            title = self.get_text("h3", listing)
            floor, price_per_m2 = self._extract_params(listing)

            yield {
                "price_text": self.get_text("strong.price", listing),
                "title": title,
                "location": self.get_text("span.location", listing),
                "description": self._extract_description(listing),
                "details_url": self.get_href("a.box-link", listing),
                "num_photos": self.get_text("span.pic-video-info-number", listing),
                "agency": self.get_text("span.re-offer-type", listing),
                "floor": floor,
                "price_per_m2": price_per_m2,
                "area": self._extract_area_from_title(title),
            }

    def get_total_pages(self, soup) -> int:
        last_page = soup.select_one("nav.paginator a.last-page")
        return int(last_page.text.strip()) if last_page else 1

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        total = self.get_total_pages(soup)
        if page_number > total:
            return None
        return current_url.replace("page=1", f"page={page_number}")
