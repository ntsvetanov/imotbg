from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import create_url_prepender, extract_property_type, to_float_or_zero

prepend_base_url = create_url_prepender("https://homes.bg")

MAX_PAGES = 30
PAGE_SIZE = 100

APARTMENTS_URL_TEMPLATE = (
    "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&typeId=ApartmentSell"
)
LAND_URL = "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=0&typeId=LandAgro"


class HomesBgParser(BaseParser):
    config = SiteConfig(
        name="homesbg",
        base_url="https://www.homes.bg",
        source_type="json",
        rate_limit_seconds=2.0,
    )

    @staticmethod
    def build_urls(config: dict) -> list[dict]:
        return config.get("urls", [])

    class Fields:
        raw_title = Field("title", None)
        property_type = Field("title", extract_property_type)
        raw_description = Field("description", None)
        city = Field("city", None)
        neighborhood = Field("neighborhood", None)
        price = Field("price_value", to_float_or_zero)
        currency = Field("price_currency", None)
        details_url = Field("details_url", prepend_base_url)
        num_photos = Field("num_photos", None)
        time = Field("time", None)
        offer_type = Field("offer_type", None)
        price_per_m2 = Field("price_per_m2", None)
        ref_no = Field("ref_no", None)

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
        return MAX_PAGES

    def get_next_page_url(self, data: dict, current_url: str, page_number: int) -> str | None:
        has_more_items = data.get("hasMoreItems", False)
        if not has_more_items:
            return None
        start_index = (page_number - 1) * PAGE_SIZE
        stop_index = page_number * PAGE_SIZE
        base_url = current_url.split("&startIndex")[0]
        return f"{base_url}&startIndex={start_index}&stopIndex={stop_index}"
