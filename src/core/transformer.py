"""
Site-agnostic transformer for normalizing raw listing data.

The Transformer converts RawListing objects (extracted from various sites)
into normalized ListingData objects with:
- Prices always in EUR
- Normalized city and neighborhood names
- Normalized property and offer types
- Computed fields (price per m2, fingerprint)
"""

import hashlib
import re
from enum import Enum

from src.core.aliases import (
    CITY_ALIASES,
    CURRENCY_ALIASES,
    OFFER_TYPE_ALIASES,
    PLOVDIV_NEIGHBORHOOD_ALIASES,
    PROPERTY_TYPE_ALIASES,
    SOFIA_NEIGHBORHOOD_ALIASES,
)
from src.core.enums import Currency
from src.core.models import ListingData, RawListing
from src.logger_setup import get_logger

logger = get_logger(__name__)


class Transformer:
    """
    Site-agnostic transformer: RawListing -> ListingData.

    All prices are converted to EUR using the fixed BGN/EUR rate.
    """

    BGN_TO_EUR_RATE = 1.9558

    def transform(self, raw_listing: RawListing) -> ListingData:
        """
        Transform a RawListing into a normalized ListingData.

        All prices are converted to EUR.
        """
        # Parse price and currency
        price, currency = self._parse_price(raw_listing.price_text)
        price_eur = self._convert_to_eur(price, currency)

        # Parse location
        city, neighborhood = self._parse_location(raw_listing.location_text)
        city = self._normalize_city(city)
        neighborhood = self._normalize_neighborhood(neighborhood, city)

        # Parse property info
        offer_type = self._extract_offer_type(raw_listing.title, raw_listing.details_url)
        property_type = self._extract_property_type(raw_listing.title, raw_listing.details_url)
        area = self._extract_area(raw_listing.area_text)
        floor = self._extract_floor(raw_listing.floor_text)

        # Fallback: infer property_type from raw_description if missing
        if not property_type and raw_listing.description:
            property_type = self._extract_property_type(raw_listing.description, None)

        # Fallback: infer floor from raw_description if missing
        if not floor and raw_listing.description:
            floor = self._extract_floor_from_description(raw_listing.description)

        # Get total_floors from raw_listing or extract from description as fallback
        total_floors = raw_listing.total_floors_text
        if not total_floors and raw_listing.description:
            total_floors = self._extract_total_floors_from_description(raw_listing.description)

        # Calculate derived fields
        price_per_m2 = self._calculate_price_per_m2(price_eur, area)

        # Build the listing
        listing = ListingData(
            site=raw_listing.site,
            search_url=raw_listing.search_url,
            details_url=raw_listing.details_url or "",
            price=price_eur,
            original_currency=self._enum_value(currency) if currency else "",
            price_per_m2=price_per_m2,
            city=city,
            neighborhood=neighborhood,
            offer_type=offer_type,
            property_type=property_type,
            area=area,
            floor=floor,
            total_floors=total_floors,
            raw_title=raw_listing.title or "",
            raw_description=raw_listing.description,
            agency=raw_listing.agency_name,
            agency_url=raw_listing.agency_url,
            num_photos=raw_listing.num_photos,
            ref_no=raw_listing.ref_no or "",
            date_time_added=raw_listing.scraped_at,
            total_offers=raw_listing.total_offers,
        )

        # Calculate fingerprint
        listing.fingerprint_hash = self._calculate_fingerprint(listing)

        return listing

    def transform_batch(self, raw_listings: list[RawListing]) -> list[ListingData]:
        """Transform multiple raw listings."""
        results = []
        for raw_listing in raw_listings:
            try:
                results.append(self.transform(raw_listing))
            except Exception as e:
                logger.warning(f"[{raw_listing.site}] Transform failed: {e}")
        return results

    # =========================================================================
    # PRICE PARSING & CONVERSION
    # =========================================================================

    def _parse_price(self, text: str | None) -> tuple[float | None, Currency | None]:
        """
        Parse price and detect currency from text.

        Args:
            text: Price text like "150 000 €" or "200000лв"

        Returns:
            Tuple of (price_value, currency_enum)
        """
        if not text:
            return None, None

        # Detect currency
        currency = self._detect_currency(text)

        # Extract numeric value (first price if multiple)
        first_price = text.split("лв")[0].split("€")[0]
        cleaned = re.sub(r"[^\d]", "", first_price.replace(" ", ""))

        price = float(cleaned) if cleaned else None
        return price, currency

    def _detect_currency(self, text: str) -> Currency | None:
        """Detect currency from price text. Prioritizes EUR."""
        if not text:
            return None

        text_lower = text.lower()

        # Check for EUR first (priority)
        for alias, currency in CURRENCY_ALIASES.items():
            if currency == Currency.EUR and alias in text_lower:
                return Currency.EUR

        # Then check for BGN
        for alias, currency in CURRENCY_ALIASES.items():
            if currency == Currency.BGN and alias in text_lower:
                return Currency.BGN

        return None

    def _convert_to_eur(self, price: float | None, currency: Currency | None) -> float | None:
        """Convert price to EUR."""
        if price is None:
            return None

        if currency == Currency.BGN:
            return round(price / self.BGN_TO_EUR_RATE, 2)

        # Already EUR or unknown currency - return as-is
        return price

    # =========================================================================
    # LOCATION PARSING
    # =========================================================================

    def _parse_location(self, text: str | None) -> tuple[str, str]:
        """
        Parse location text into city and neighborhood.

        Handles various formats:
        - "гр. София, Лозенец"
        - "София / Лозенец"
        - "Лозенец, София"

        Returns:
            Tuple of (city, neighborhood)
        """
        if not text:
            return "", ""

        # Clean up text
        text = text.replace("\xa0", " ").replace("&nbsp;", " ").strip()

        # Try to detect format and extract parts
        # Format: "гр. X, Y" or "град X, Y"
        match = re.search(r"(?:гр\.|град)\s*([^,/]+)[,/]\s*(.+)", text, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            neighborhood = match.group(2).strip()
            # Strip neighborhood prefix if present
            neighborhood = re.sub(r"^(?:кв\.|квартал)\s*", "", neighborhood, flags=re.IGNORECASE)
            return city, neighborhood.strip()

        # Format: "X / Y" (city / neighborhood)
        if " / " in text:
            parts = text.split(" / ", 1)
            city_part = re.sub(r"^(?:гр\.|град|с\.)\s*", "", parts[0], flags=re.IGNORECASE)
            neighborhood_part = re.sub(r"^(?:кв\.|квартал)\s*", "", parts[1], flags=re.IGNORECASE)
            return city_part.strip(), neighborhood_part.strip()

        # Format: "X, Y" (city, neighborhood)
        if ", " in text:
            parts = text.split(", ", 1)
            city_part = re.sub(r"^(?:гр\.|град|с\.)\s*", "", parts[0], flags=re.IGNORECASE)
            return city_part.strip(), parts[1].strip()

        # Single part - assume it's the city
        city_part = re.sub(r"^(?:гр\.|град|с\.)\s*", "", text, flags=re.IGNORECASE)
        return city_part.strip(), ""

    def _normalize_city(self, city: str) -> str:
        """Normalize city name using alias lookup."""
        if not city:
            return ""

        city_lower = city.lower().strip()

        # Try exact match
        if city_lower in CITY_ALIASES:
            return CITY_ALIASES[city_lower].value

        # Try substring match
        for alias, city_enum in CITY_ALIASES.items():
            if alias in city_lower:
                return city_enum.value

        # Return original if not found
        return city.strip()

    def _normalize_neighborhood(self, neighborhood: str, city: str = "") -> str:
        """Normalize neighborhood name based on city context."""
        if not neighborhood:
            return ""

        # Clean up
        neighborhood_clean = neighborhood.lower().strip()
        neighborhood_clean = re.sub(r"^(?:кв\.|квартал|ж\.к\.|ж\.к|жк)\s*", "", neighborhood_clean)
        neighborhood_clean = neighborhood_clean.strip()

        # Determine which city's neighborhoods to check
        is_sofia = "соф" in city.lower() if city else False
        is_plovdiv = "плов" in city.lower() if city else False

        # Check appropriate alias dict
        if is_sofia:
            result = self._find_neighborhood(neighborhood_clean, SOFIA_NEIGHBORHOOD_ALIASES)
            if result:
                return result
        elif is_plovdiv:
            result = self._find_neighborhood(neighborhood_clean, PLOVDIV_NEIGHBORHOOD_ALIASES)
            if result:
                return result
        else:
            # Try both (Sofia first)
            result = self._find_neighborhood(neighborhood_clean, SOFIA_NEIGHBORHOOD_ALIASES)
            if result:
                return result
            result = self._find_neighborhood(neighborhood_clean, PLOVDIV_NEIGHBORHOOD_ALIASES)
            if result:
                return result

        # Return cleaned version if not found
        return neighborhood_clean.title() if neighborhood_clean else neighborhood

    def _find_neighborhood(self, text: str, aliases: dict) -> str | None:
        """Find neighborhood in alias dict."""
        # Exact match
        if text in aliases:
            return aliases[text].value

        # Substring match (longer patterns first)
        for alias in sorted(aliases.keys(), key=len, reverse=True):
            if alias in text:
                return aliases[alias].value

        return None

    # =========================================================================
    # PROPERTY PARSING
    # =========================================================================

    def _extract_offer_type(self, title: str | None, url: str | None) -> str:
        """Extract and normalize offer type from title or URL."""
        # Try URL first (more reliable)
        if url:
            result = self._find_in_aliases(url, OFFER_TYPE_ALIASES)
            if result:
                return result.value

        # Try title
        if title:
            result = self._find_in_aliases(title, OFFER_TYPE_ALIASES)
            if result:
                return result.value

        return ""

    def _extract_property_type(self, title: str | None, url: str | None) -> str:
        """Extract and normalize property type from title or URL."""
        # Try URL first
        if url:
            result = self._find_in_aliases(url, PROPERTY_TYPE_ALIASES)
            if result:
                return result.value

        # Try title
        if title:
            result = self._find_in_aliases(title, PROPERTY_TYPE_ALIASES)
            if result:
                return result.value

        return ""

    def _extract_area(self, text: str | None) -> float | None:
        """
        Extract area from text.

        Handles: "56 кв.м", "207.43 м²", "Площ: 251.01 м²"
        """
        if not text:
            return None

        match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:кв\.?\s*)?м", text)
        if match:
            try:
                return float(match.group(1).replace(",", "."))
            except ValueError:
                return None
        return None

    def _extract_floor(self, text: str | None) -> str:
        """
        Extract floor from text.

        Handles: "Етаж: 3", "6-ти ет.", "ет. 3", "партер", plain "3"
        """
        if not text:
            return ""

        # Try "Етаж:" pattern first
        match = re.search(r"Етаж:\s*(\d+|партер|последен)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try patterns like "6-ти ет.", "ет. 3", "3 ет."
        match = re.search(r"(\d+)(?:-\w+)?\s*ет\.?|ет\.?\s*(\d+)", text)
        if match:
            return match.group(1) or match.group(2)

        # Try plain number (must be the entire string or standalone)
        match = re.search(r"^(\d+)$", text.strip())
        if match:
            return match.group(1)

        return ""

    def _extract_floor_from_description(self, text: str | None) -> str:
        """
        Extract floor from description text (fallback).

        Handles patterns like:
        - "на 3-ти етаж"
        - "етаж 5"
        - "5 етаж"
        - "партерен етаж"
        """
        if not text:
            return ""

        # Try "на X етаж" or "X-ти етаж" patterns
        match = re.search(r"(?:на\s+)?(\d+)(?:-\w+)?\s*етаж", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try "етаж X" pattern
        match = re.search(r"етаж\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try "партерен" or "партер"
        if re.search(r"\bпартер(?:ен|а)?\b", text, re.IGNORECASE):
            return "партер"

        return ""

    def _extract_total_floors_from_description(self, text: str | None) -> str | None:
        """
        Extract total floors from description text (fallback).

        Handles patterns like:
        - "8-ми ет. от 8" -> "8"
        - "3-ти етаж от 8" -> "8"
        - "на 3-ти етаж от 8 в панелн" -> "8"
        """
        if not text:
            return None

        # Pattern: "X-ти/ми/ри ет./етаж от Y"
        match = re.search(r"\d+(?:-\w+)?\s*(?:ет\.?|етаж)\s*от\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================

    def _calculate_price_per_m2(self, price: float | None, area: float | None) -> float | None:
        """Calculate price per square meter."""
        if not price or not area or area <= 0:
            return None
        return round(price / area, 2)

    def _calculate_fingerprint(self, listing: ListingData) -> str:
        """
        Calculate fingerprint hash for duplicate detection.

        Based on: price (rounded to 100) + area (integer) + property_type + city
        """
        # Normalize price (round to nearest 100)
        price_norm = ""
        if listing.price:
            price_norm = str(int(round(listing.price / 100) * 100))

        # Normalize area (integer)
        area_norm = ""
        if listing.area:
            area_norm = str(int(listing.area))

        fingerprint = f"{price_norm}|{area_norm}|{listing.property_type}|{listing.city}"
        return hashlib.md5(fingerprint.encode()).hexdigest()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _find_in_aliases(self, text: str, aliases: dict) -> Enum | None:
        """Search for any alias within text (substring match)."""
        if not text:
            return None

        text_lower = text.lower()
        # Sort by length descending to match longer patterns first
        for alias in sorted(aliases.keys(), key=len, reverse=True):
            if alias in text_lower:
                return aliases[alias]
        return None

    def _enum_value(self, enum_val: Enum | str | None) -> str:
        """Extract value from enum or return string as-is."""
        if enum_val is None:
            return ""
        if hasattr(enum_val, "value"):
            return enum_val.value
        return str(enum_val)
