import re

from src.core.enums import OfferType
from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import (
    extract_currency,
    extract_offer_type,
    extract_property_type,
    is_without_dds,
    parse_price,
)
from src.core.normalization import normalize_city, normalize_neighborhood


def extract_city_from_location(location: str) -> str:
    """Extract city from location like 'гр. София / кв. Лозенец' or 'с. Панчарево'"""
    if not location:
        return ""
    # Remove HTML entities and clean up
    location = location.replace("\xa0", " ").replace("&nbsp;", " ")
    # Look for "гр. X" or "с. X" pattern
    match = re.search(r"(?:гр\.|с\.)\s*([\w\s-]+?)(?:\s*/|<br|$)", location, re.IGNORECASE)
    if match:
        city = match.group(1).strip()
    else:
        # Try to get first part before /
        parts = location.split("/")
        city = parts[0].strip() if parts else ""
        # Remove prefixes
        city = re.sub(r"^(?:гр\.|с\.)\s*", "", city)

    result = normalize_city(city)
    return result.value if hasattr(result, "value") else result


def extract_neighborhood_from_location(location: str) -> str:
    """Extract neighborhood from location like 'гр. София / кв. Лозенец'"""
    if not location:
        return ""
    location = location.replace("\xa0", " ").replace("&nbsp;", " ")
    # Look for "кв. X" pattern
    match = re.search(r"кв\.\s*([\w\s-]+)", location, re.IGNORECASE)
    if match:
        neighborhood = match.group(1).strip()
    else:
        # Try second part after /
        parts = location.split("/")
        if len(parts) > 1:
            neighborhood = parts[1].strip()
            neighborhood = re.sub(r"^кв\.\s*", "", neighborhood)
        else:
            return ""

    # Get city for context-aware normalization
    city = extract_city_from_location(location)
    result = normalize_neighborhood(neighborhood, city)
    return result.value if hasattr(result, "value") else result


def extract_area(area_text: str) -> str:
    """Extract area from text like 'Площ: 251.01 м²'"""
    if not area_text:
        return ""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*м", area_text)
    return match.group(1).replace(",", ".") if match else ""


def extract_floor(floor_text: str) -> str:
    """Extract floor from text like 'Етаж: 3' or 'Етаж: партер'"""
    if not floor_text:
        return ""
    match = re.search(r"Етаж:\s*(\d+|партер|последен)", floor_text, re.IGNORECASE)
    return match.group(1) if match else ""


def extract_ref_from_contact_url(url: str) -> str:
    """Extract reference number from contact URL like 'ref_no=SOF 109946'"""
    if not url:
        return ""
    match = re.search(r"ref_no=([^&\"']+)", url)
    return match.group(1).strip() if match else ""


def calculate_price_per_m2(raw: dict) -> str:
    """Calculate price per m2 from price_text and details_text"""
    try:
        price = parse_price(raw.get("price_text", ""))
        area_str = extract_area(raw.get("details_text", ""))
        if price and area_str:
            area = float(area_str)
            if area > 0:
                return str(round(price / area, 2))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return ""


class SuprimmoParser(BaseParser):
    config = SiteConfig(
        name="suprimmo",
        base_url="https://www.suprimmo.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.5,
    )

    class Fields:
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        without_dds = Field("price_text", is_without_dds)
        city = Field("location", extract_city_from_location)
        neighborhood = Field("location", extract_neighborhood_from_location)
        raw_title = Field("title")
        property_type = Field("title", extract_property_type)
        offer_type = Field("offer_type")
        raw_description = Field("description")
        details_url = Field("details_url")
        area = Field("details_text", extract_area)
        floor = Field("details_text", extract_floor)
        ref_no = Field("ref_no")
        agency = Field("agency_name")
        num_photos = Field("num_photos")
        total_offers = Field("total_offers")
        price_per_m2 = Field("price_per_m2")

    def _extract_total_offers(self, soup) -> int:
        """Extract total offers count from page like '1448 намерени оферти'"""
        # Look for the count in the page header
        count_elem = soup.select_one("p.font-medium.font-semibold")
        if count_elem:
            text = count_elem.get_text(strip=True)
            match = re.search(r"(\d+)\s*намерени", text)
            if match:
                return int(match.group(1))
        return 0

    def extract_listings(self, soup):
        # Extract total offers from the page (only once per page)
        total_offers = self._extract_total_offers(soup)

        # Try to determine default offer type from page URL/context
        # Check if page is a sales or rent page by looking at dataLayer or page content
        default_offer_type = ""
        datalayer = soup.select_one("script:-soup-contains('listing_pagetype')")
        if datalayer:
            text = datalayer.get_text().lower()
            if "type:'продава'" in text or "type:'продажба'" in text:
                default_offer_type = "продава"
            elif "type:'наем'" in text:
                default_offer_type = "наем"

        # Find all property cards - they have class "panel rel shadow offer"
        for card in soup.select("div.panel.offer"):
            # Get property ID from data attribute
            prop_id = card.get("data-prop-id", "")

            # Extract details URL from the link
            details_link = card.select_one("a.lnk")
            details_url = details_link.get("href", "") if details_link else ""

            # Fallback to button link
            if not details_url:
                btn_link = card.select_one("div.foot a.button[href*='/imot-']")
                details_url = btn_link.get("href", "") if btn_link else ""

            # Extract title from div.ttl
            title_elem = card.select_one("div.ttl")
            title = ""
            if title_elem:
                # Get text without the info icon
                for icon in title_elem.select("i"):
                    icon.decompose()
                title = title_elem.get_text(strip=True)

            # Extract price from div.prc
            price_elem = card.select_one("div.prc")
            price_text = ""
            if price_elem:
                price_text = price_elem.get_text(separator=" ", strip=True)
                # Try to extract EUR price specifically
                eur_match = re.search(r"([\d\s]+)\s*€", price_text.replace("\xa0", " "))
                if eur_match:
                    price_text = eur_match.group(1).strip() + " €"

            # Extract location from div.loc
            location_elem = card.select_one("div.loc")
            location = ""
            if location_elem:
                # Remove map marker link
                for marker in location_elem.select("a.property_map"):
                    marker.decompose()
                location = location_elem.get_text(separator=" / ", strip=True)

            # Extract details (area, floor, etc.) from div.lst
            details_elem = card.select_one("div.lst")
            details_text = details_elem.get_text(strip=True) if details_elem else ""

            # Extract reference number from agent contact link
            agent_link = card.select_one("a.offer-agent-form")
            ref_no = ""
            if agent_link:
                ref_no = extract_ref_from_contact_url(agent_link.get("href", ""))

            # If no ref_no from link, try from prop_id
            if not ref_no and prop_id:
                ref_no = prop_id

            # Determine offer type from URL first, then fall back to page context
            offer_type = extract_offer_type("", details_url)
            # If offer_type is not a known value (продава or наем), use default
            if offer_type not in (OfferType.SALE.value, OfferType.RENT.value):
                offer_type = default_offer_type

            # Count photos
            photos = card.select("div.slider-embed div.item")
            num_photos = len(photos)

            # Build raw listing dict
            raw = {
                "price_text": price_text,
                "title": title,
                "location": location,
                "details_text": details_text,
                "description": "",
                "details_url": details_url,
                "ref_no": ref_no,
                "offer_type": offer_type,
                "agency_name": "Suprimmo",
                "num_photos": num_photos,
                "total_offers": total_offers,
            }

            # Calculate price per m2
            raw["price_per_m2"] = calculate_price_per_m2(raw)

            yield raw

    def get_total_pages(self, soup) -> int:
        """Extract total pages from '1448 намерени оферти / Страницa 1 от 61'"""
        count_elem = soup.select_one("p.font-medium.font-semibold")
        if count_elem:
            text = count_elem.get_text(strip=True)
            # Look for "Страницa X от Y" pattern
            match = re.search(r"от\s*(\d+)", text)
            if match:
                return int(match.group(1))

        # Fallback: Check for rel="next" link in head
        next_link = soup.select_one("link[rel='next']")
        if next_link:
            return self.config.max_pages
        return 1

    def get_next_page_url(self, soup, current_url: str, page_number: int) -> str | None:
        # Check if there are any listings on current page
        has_items = bool(soup.select("div.panel.offer"))
        if not has_items:
            return None

        # Check for next page link in HTML head - this is the key indicator
        # If there's no rel="next" link, we're on the last page
        next_link = soup.select_one("link[rel='next']")
        if not next_link:
            return None

        # For page 2, use the rel="next" link from page 1
        if page_number == 2:
            return next_link.get("href")

        # Suprimmo uses: /page/2/, /page/3/, etc.
        # Base URL without trailing slash and page suffix
        base_url = re.sub(r"/page/\d+/?$", "", current_url.rstrip("/"))

        # Construct next page URL
        next_url = f"{base_url}/page/{page_number}/"

        return next_url
