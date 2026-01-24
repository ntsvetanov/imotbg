import re
from bs4 import Comment

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_currency,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
)


def extract_city(location: str) -> str:
    if not location:
        return ""
    parts = location.split(",")
    return parts[0].strip() if parts else ""


def extract_neighborhood(location: str) -> str:
    if not location:
        return ""
    parts = location.split(",")
    return parts[1].strip() if len(parts) > 1 else ""


def extract_area(location_info: str) -> str:
    if not location_info:
        return ""
    match = re.search(r"(\d+)\s*кв\.м", location_info)
    return f"{match.group(1)} кв.м" if match else ""


def extract_area_numeric(location_info: str) -> str:
    """Extract numeric area value for price_per_m2 calculation."""
    if not location_info:
        return ""
    match = re.search(r"(\d+)\s*кв\.м", location_info)
    return match.group(1) if match else ""


def extract_ref_from_url(url: str) -> str:
    """Extract reference number from URL like /obiava/23458881/..."""
    if not url:
        return ""
    match = re.search(r"/obiava/(\d+)/", url)
    return match.group(1) if match else ""


def calculate_price_per_m2(raw: dict) -> str:
    """Calculate price per m2 from price_text and location_info."""
    try:
        price = parse_price(raw.get("price_text", ""))
        area_str = extract_area_numeric(raw.get("location_info", ""))
        if price and area_str:
            area = float(area_str)
            if area > 0:
                return str(round(price / area, 2))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return ""


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
        agency_name = Field("agency_name")
        agency_url = Field("agency_url")
        ref_no = Field("ref_no")
        total_offers = Field("total_offers")
        time = Field("time")
        num_photos = Field("num_photos")
        price_per_m2 = Field("price_per_m2")

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

    def _extract_time_from_comment(self, item) -> str:
        """Extract time from HTML comment like <!-- 10:07 часа от 29.12.2025-->"""
        for comment in item.find_all(string=lambda text: isinstance(text, Comment)):
            match = re.search(r"(\d{1,2}:\d{2})\s*часа\s*от\s*(\S+)", comment)
            if match:
                time_str = match.group(1)
                date_str = match.group(2)
                if date_str == "днес":
                    return f"{time_str} днес"
                return f"{time_str} {date_str}"
        return ""

    def _extract_num_photos(self, item) -> int:
        """Count number of photos - on list page there's only 1 photo per item."""
        photo_div = item.select_one("div.photo img")
        return 1 if photo_div else 0

    def _extract_total_offers(self, soup) -> int:
        """Extract total offers count from page like '1 - 20 от общо 2000+ обяви'"""
        # Look for pattern in page - the total count is in a strong tag
        page_info = soup.find(string=re.compile(r"от общо"))
        if page_info:
            parent = page_info.parent if page_info.parent else None
            if parent:
                text = parent.get_text()
                match = re.search(r"от общо\s*(\d+)", text.replace("+", ""))
                if match:
                    return int(match.group(1))
        return 0

    def _extract_agency_info(self, item) -> tuple[str, str]:
        """Extract agency name from description text.

        On the list page, agency info is often embedded in the description text.
        Returns tuple of (agency_name, agency_url).
        """
        # On the list page, agency info is usually in the description
        info_div = item.select_one("div.info")
        if not info_div:
            return "", ""

        # Get full text and look for common agency patterns
        full_text = info_div.get_text(strip=True)

        # Look for "Агенция" or common agency name patterns
        agency_patterns = [
            r"Агенция\s+(?:за\s+недвижими\s+имоти\s+)?([A-Za-zА-Яа-я\s]+?)(?:\s+(?:предлага|представя|има|с\s+удоволствие))",
            r"([A-Za-z\s]+(?:Estate|Properties|Estates|Real Estate|Имоти|Пропърти)s?)",
        ]

        for pattern in agency_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                agency_name = match.group(1).strip()
                # Clean up common suffixes
                agency_name = re.sub(r"\s+(предлага|представя|има|с)$", "", agency_name)
                if len(agency_name) > 3:  # Avoid false positives
                    return agency_name, ""

        return "", ""

    def extract_listings(self, soup):
        list_container = soup.select_one("div.list")
        if not list_container:
            return

        # Extract total offers from the page (only once per page)
        total_offers = self._extract_total_offers(soup)

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

            # Extract ref_no from details_url
            ref_no = extract_ref_from_url(details_url) if details_url else ""

            # Extract time from HTML comment
            time = self._extract_time_from_comment(item)

            # Extract num_photos
            num_photos = self._extract_num_photos(item)

            # Extract agency info from description
            agency_name, agency_url = self._extract_agency_info(item)

            raw = {
                "price_text": price_text,
                "title": title,
                "location": location,
                "location_info": location_info,
                "description": description,
                "details_url": details_url,
                "contact_info": contact_info,
                "ref_no": ref_no,
                "total_offers": total_offers,
                "time": time,
                "num_photos": num_photos,
                "agency_name": agency_name,
                "agency_url": agency_url,
            }

            # Calculate price per m2
            raw["price_per_m2"] = calculate_price_per_m2(raw)

            yield raw

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
