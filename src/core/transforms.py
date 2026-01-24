"""
Transform functions for property listing data.

These functions are used to extract and normalize data from raw scraped content.
The normalization module is used for enum-based normalization.
"""

import re
from enum import Enum

from src.core.enums import OfferType
from src.core.normalization import (
    normalize_agency,
    normalize_city,
    normalize_currency,
    normalize_neighborhood,
    normalize_offer_type,
    normalize_property_type,
)

__all__ = [
    "calculate_price_per_m2",
    "enum_value_or_str",
    "extract_agency",
    "extract_area",
    "extract_city",
    "extract_city_with_prefix",
    "extract_currency",
    "extract_floor",
    "extract_neighborhood",
    "extract_neighborhood_with_prefix",
    "extract_offer_type",
    "extract_property_type",
    "is_valid_offer_type",
    "is_without_dds",
    "parse_price",
    "to_float_or_zero",
    "to_float_safe",
    "to_int_safe",
]


def enum_value_or_str(result: Enum | str) -> str:
    """Extract value from enum or return string as-is."""
    return result.value if isinstance(result, Enum) else result


def parse_price(text: str) -> float:
    """
    Parse price from text, handling various formats.

    Args:
        text: Price text like "150 000 €" or "200000лв"

    Returns:
        Parsed price as float, or 0.0 if parsing fails
    """
    if not text:
        return 0.0
    first_price = text.split("лв")[0].split("€")[0]
    cleaned = re.sub(r"[^\d]", "", first_price.replace(" ", ""))
    return float(cleaned) if cleaned else 0.0


def extract_currency(text: str) -> str:
    """
    Extract and normalize currency from price text.

    Args:
        text: Price text containing currency symbol

    Returns:
        Normalized currency string (EUR or BGN)
    """
    return enum_value_or_str(normalize_currency(text))


def is_without_dds(text: str) -> bool:
    """
    Check if price is without VAT (ДДС).

    Args:
        text: Price text that may contain VAT indicator

    Returns:
        True if price is marked as without VAT
    """
    return "ддс" in text.lower() if text else False


def extract_city(location: str) -> str:
    """
    Extract and normalize city from location string.

    Args:
        location: Location string like "гр. София, Лозенец"

    Returns:
        Normalized city name
    """
    return enum_value_or_str(normalize_city(location))


def extract_neighborhood(location: str, city: str = "") -> str:
    """
    Extract and normalize neighborhood from location string.

    Args:
        location: Location string like "гр. София, Лозенец"
        city: Optional city for context-aware normalization

    Returns:
        Normalized neighborhood name or empty string if not found
    """
    if not location:
        return ""
    parts = location.split(",")
    neighborhood = parts[1].strip() if len(parts) > 1 else ""
    if not neighborhood:
        return ""
    return enum_value_or_str(normalize_neighborhood(neighborhood, city))


def extract_property_type(text: str, url: str = "") -> str:
    """
    Extract and normalize property type from text and/or URL.

    Args:
        text: Text content (e.g., title) to search
        url: URL to search for patterns

    Returns:
        Normalized property type string
    """
    return enum_value_or_str(normalize_property_type(text, url))


def extract_offer_type(text: str, url: str = "") -> str:
    """
    Extract and normalize offer type from text and/or URL.

    Args:
        text: Text content (e.g., title) to search
        url: URL to search for patterns

    Returns:
        Normalized offer type string (продава or наем)
    """
    return enum_value_or_str(normalize_offer_type(text, url))


def extract_agency(text: str) -> str:
    """
    Extract and normalize agency name.

    Args:
        text: Agency name text

    Returns:
        Normalized agency name
    """
    return normalize_agency(text)


def to_int_safe(text: str) -> int:
    """
    Safely convert text to integer.

    Args:
        text: Text containing a number

    Returns:
        Extracted integer, or 0 if parsing fails
    """
    if not text:
        return 0
    match = re.search(r"\d+", str(text))
    return int(match.group()) if match else 0


def to_float_safe(text: str) -> float:
    """
    Safely convert text to float.

    Args:
        text: Text containing a number

    Returns:
        Extracted float, or 0.0 if parsing fails
    """
    if not text:
        return 0.0
    match = re.search(r"[\d.]+", str(text))
    return float(match.group()) if match else 0.0


def to_float_or_zero(value) -> float:
    """
    Convert value to float, returning 0.0 on failure.

    Args:
        value: Value to convert (can be str, int, float)

    Returns:
        Float value, or 0.0 if conversion fails
    """
    if not value:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").replace(" ", "").split()[0]
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_area(text: str) -> str:
    """
    Extract area from text containing square meters.

    Handles various formats:
    - "Площ: 251.01 м²"
    - "56 кв.м, 6-ти ет."
    - "207.43 м²"

    Args:
        text: Text containing area information

    Returns:
        Area as string (e.g., "251.01") or empty string if not found
    """
    if not text:
        return ""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:кв\.?\s*)?м", text)
    return match.group(1).replace(",", ".") if match else ""


def extract_floor(text: str) -> str:
    """
    Extract floor number from text.

    Handles various formats:
    - "Етаж: 3"
    - "Етаж: партер"
    - "6-ти ет. от 8"
    - "ет. 3"

    Args:
        text: Text containing floor information

    Returns:
        Floor as string (number or "партер"/"последен") or empty string
    """
    if not text:
        return ""
    # Try explicit "Етаж:" pattern first
    match = re.search(r"Етаж:\s*(\d+|партер|последен)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    # Try patterns like "6-ти ет.", "ет. 3", "3 ет."
    match = re.search(r"(\d+)(?:-\w+)?\s*ет\.?|ет\.?\s*(\d+)", text)
    if match:
        return match.group(1) or match.group(2)
    return ""


def calculate_price_per_m2(price: float, area_str: str) -> str:
    """
    Calculate price per square meter.

    Args:
        price: Price value
        area_str: Area as string (e.g., "75.5")

    Returns:
        Price per m2 as string, or empty string if calculation fails
    """
    if not price or not area_str:
        return ""
    try:
        area = float(area_str)
        if area > 0:
            return str(round(price / area, 2))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return ""


def extract_city_with_prefix(location: str, separator: str = "/") -> str:
    """
    Extract city from location that may have prefixes like "гр." or "с.".

    Handles formats like:
    - "гр. София / кв. Лозенец"
    - "с. Панчарево"
    - "София, Лозенец"

    Args:
        location: Full location string
        separator: Separator between city and neighborhood (default "/")

    Returns:
        Normalized city name
    """
    if not location:
        return ""
    location = location.replace("\xa0", " ").replace("&nbsp;", " ")

    # Try to match "гр. X" or "с. X" pattern
    match = re.search(
        rf"(?:гр\.|град|с\.)\s*([\w\s-]+?)(?:\s*{re.escape(separator)}|<br|$)",
        location,
        re.IGNORECASE,
    )
    if match:
        city = match.group(1).strip()
    else:
        # Fallback: take first part before separator
        parts = location.split(separator)
        city = parts[0].strip()
        # Remove prefixes
        city = re.sub(r"^(?:гр\.|град|с\.)\s*", "", city, flags=re.IGNORECASE)

    return enum_value_or_str(normalize_city(city))


def extract_neighborhood_with_prefix(location: str, separator: str = "/") -> str:
    """
    Extract neighborhood from location that may have prefixes like "кв.".

    Handles formats like:
    - "гр. София / кв. Лозенец"
    - "София, Център"

    Args:
        location: Full location string
        separator: Separator between city and neighborhood (default "/")

    Returns:
        Normalized neighborhood name or empty string
    """
    if not location:
        return ""
    location = location.replace("\xa0", " ").replace("&nbsp;", " ")

    # Try to match "кв. X" pattern
    match = re.search(r"кв\.\s*([\w\s-]+?)(?:\s*\(|$|Област)", location, re.IGNORECASE)
    if match:
        neighborhood = match.group(1).strip()
    else:
        # Fallback: take second part after separator
        parts = location.split(separator)
        if len(parts) > 1:
            neighborhood = parts[1].strip()
            # Remove "кв." prefix if present
            neighborhood = re.sub(r"^кв\.\s*", "", neighborhood, flags=re.IGNORECASE)
            # Remove region info
            neighborhood = re.sub(r"\s*(?:Област|\().*$", "", neighborhood)
            neighborhood = neighborhood.strip()
        else:
            return ""

    city = extract_city_with_prefix(location, separator)
    return enum_value_or_str(normalize_neighborhood(neighborhood, city))


def is_valid_offer_type(offer_type: str) -> bool:
    """Check if offer_type is a valid known value."""
    return offer_type in (OfferType.SALE.value, OfferType.RENT.value)
