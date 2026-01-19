from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import extract_property_type, to_float_or_zero


class HomesBgParser(BaseParser):
    config = SiteConfig(
        name="homesbg",
        base_url="https://www.homes.bg",
        source_type="json",
        rate_limit_seconds=2.0,
        max_pages=30,
        page_size=100,
    )

    class Fields:
        raw_title = Field("title")
        property_type = Field("title", extract_property_type)
        raw_description = Field("description")
        city = Field("city")
        neighborhood = Field("neighborhood")
        price = Field("price_value", to_float_or_zero)
        currency = Field("price_currency")
        details_url = Field("details_url", prepend_url=True)
        num_photos = Field("num_photos")
        time = Field("time")
        offer_type = Field("offer_type")
        price_per_m2 = Field("price_per_m2")
        ref_no = Field("ref_no")

    def _parse_location(self, location: str) -> tuple[str, str]:
        if not location:
            return "", ""
        parts = location.split(",")
        neighborhood = parts[0].strip()
        city = parts[1].strip() if len(parts) > 1 else ""
        return city, neighborhood

    def _determine_offer_type(self, search_criteria: dict) -> str:
        type_id = search_criteria.get("typeId", "")
        return "продава" if "Sell" in type_id else "наем"

    def extract_listings(self, data: dict):
        search_criteria = data.get("searchCriteria", {})
        offer_type = self._determine_offer_type(search_criteria)

        for item in data.get("result", []):
            location = item.get("location", "")
            city, neighborhood = self._parse_location(location)
            price_data = item.get("price", {})

            yield {
                "title": item.get("title"),
                "description": item.get("description"),
                "city": city,
                "neighborhood": neighborhood,
                "price_value": price_data.get("value"),
                "price_currency": price_data.get("currency"),
                "price_per_m2": price_data.get("pricePerSquareMeter", ""),
                "details_url": item.get("viewHref"),
                "num_photos": len(item.get("photos", [])),
                "time": item.get("time"),
                "offer_type": offer_type,
                "ref_no": str(item.get("id", "")),
            }

    def get_total_pages(self, data: dict) -> int:
        return self.config.max_pages

    def get_next_page_url(self, data: dict, current_url: str, page_number: int) -> str | None:
        if not data.get("hasMoreItems", False):
            return None
        start_index = (page_number - 1) * self.config.page_size
        stop_index = page_number * self.config.page_size
        base_url = current_url.split("&startIndex")[0]
        return f"{base_url}&startIndex={start_index}&stopIndex={stop_index}"
