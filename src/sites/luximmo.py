import re

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_currency,
    extract_property_type,
    is_without_dds,
    parse_price,
)


def extract_city(location: str) -> str:
    """Extract city from location like 'гр. София / кв. Лозенец'"""
    if not location:
        return ""
    # Look for pattern like "гр. София" or just take first part
    match = re.search(r"(?:гр\.\s*|град\s*)?([\w\s]+?)(?:\s*/|$)", location)
    if match:
        return match.group(1).strip()
    parts = location.split("/")
    return parts[0].strip() if parts else ""


def extract_neighborhood(location: str) -> str:
    """Extract neighborhood from location like 'гр. София / кв. Лозенец'"""
    if not location:
        return ""
    # Look for kv. pattern or second part after /
    match = re.search(r"кв\.\s*([\w\s]+)", location)
    if match:
        return match.group(1).strip()
    parts = location.split("/")
    if len(parts) > 1:
        neighborhood = parts[1].strip()
        # Remove "кв." prefix if present
        return re.sub(r"^кв\.\s*", "", neighborhood)
    return ""


def extract_area(area_text: str) -> str:
    """Extract area number from text like '207.43 м²'"""
    if not area_text:
        return ""
    match = re.search(r"(\d+(?:[.,]\d+)?)", area_text)
    return match.group(1).replace(",", ".") if match else ""


def extract_ref_from_url(url: str) -> str:
    """Extract reference number from URL like 'luksozen-imot-43445-...'"""
    if not url:
        return ""
    match = re.search(r"imot-(\d+)", url)
    return match.group(1) if match else ""


class LuximmoParser(BaseParser):
    config = SiteConfig(
        name="luximmo",
        base_url="https://www.luximmo.bg",
        encoding="utf-8",
        rate_limit_seconds=1.5,
    )

    class Fields:
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        without_dds = Field("price_text", is_without_dds)
        city = Field("location", extract_city)
        neighborhood = Field("location", extract_neighborhood)
        raw_title = Field("title")
        property_type = Field("title", extract_property_type)
        offer_type = Field("offer_type")
        raw_description = Field("description")
        details_url = Field("details_url")
        area = Field("area_text", extract_area)
        ref_no = Field("ref_no")
        floor = Field("floor")
        agency_name = Field("agency_name")

    def extract_listings(self, soup):
        # Find all property cards
        for card in soup.select("div.card.mb-4"):
            # Skip if no card-url (not a property listing)
            url_elem = card.select_one("a.card-url")
            if not url_elem:
                continue

            details_url = url_elem.get("href", "")

            # Extract title
            title_elem = card.select_one("h4.card-title")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract price - look for the Euro price
            price_elem = card.select_one(".card-price")
            price_text = ""
            if price_elem:
                # Get text content, prefer EUR
                price_text = price_elem.get_text(strip=True)
                # Try to find the EUR value specifically
                eur_match = re.search(r"([\d\s]+)\s*€", price_text.replace("\xa0", " "))
                if eur_match:
                    price_text = eur_match.group(1).replace(" ", "") + " €"

            # Extract location
            location_elem = card.select_one(".card-loc-dis .text-dark")
            location = ""
            if location_elem:
                location = location_elem.get_text(separator=" ", strip=True)
                # Clean up the location string
                location = re.sub(r"\s+", " ", location)

            # Extract area
            area_text = ""
            area_elem = card.select_one(".card-dis")
            if area_elem:
                area_match = re.search(r"Площ:\s*([\d.,]+\s*м)", area_elem.get_text())
                if area_match:
                    area_text = area_match.group(1)

            # Extract floor
            floor = ""
            if area_elem:
                floor_match = re.search(r"Етаж:\s*(\d+)", area_elem.get_text())
                if floor_match:
                    floor = floor_match.group(1)

            # Extract reference number from URL
            ref_no = extract_ref_from_url(details_url)

            # Extract offer type from URL or title
            offer_type = ""
            if "pod-naem" in details_url or "наем" in title.lower():
                offer_type = "наем"
            elif "za-prodajba" in details_url or "продажба" in title.lower():
                offer_type = "продава"

            yield {
                "price_text": price_text,
                "title": title,
                "location": location,
                "area_text": area_text,
                "floor": floor,
                "description": "",
                "details_url": details_url,
                "ref_no": ref_no,
                "offer_type": offer_type,
                "agency_name": "Luximmo",
            }

    def get_total_pages(self, soup) -> int:
        """Extract total pages from pagination"""
        pagination = soup.select_one("ul.pagination")
        if not pagination:
            return 1

        max_page = 1
        for link in pagination.select("a.page-link"):
            href = link.get("href", "")
            # Match indexN.html pattern
            match = re.search(r"index(\d+)\.html", href)
            if match:
                page_num = int(match.group(1)) + 1  # index0 = page 2, etc.
                max_page = max(max_page, page_num)
            # Also check text content for last page number
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))

        return max_page

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        # Check if there are any listings on current page
        has_items = bool(soup.select("div.card.mb-4 a.card-url"))
        if not has_items:
            return None

        total = self.get_total_pages(soup)
        if page_number > total:
            return None

        # Luximmo uses: index.html (page 1), index1.html (page 2), index2.html (page 3), etc.
        # So page_number 2 -> index1.html, page_number 3 -> index2.html
        page_index = page_number - 1  # Convert to 0-based index for URL

        # Replace the index part of the URL
        if "index.html" in current_url:
            if page_index == 0:
                return current_url  # Stay on index.html for page 1
            return current_url.replace("index.html", f"index{page_index}.html")
        elif re.search(r"index\d+\.html", current_url):
            if page_index == 0:
                return re.sub(r"index\d+\.html", "index.html", current_url)
            return re.sub(r"index\d+\.html", f"index{page_index}.html", current_url)
        else:
            # URL doesn't have index pattern, append it
            if current_url.endswith("/"):
                return f"{current_url}index{page_index}.html" if page_index > 0 else f"{current_url}index.html"
            return f"{current_url}/index{page_index}.html" if page_index > 0 else f"{current_url}/index.html"
