"""
Transform functions for property listing data.

These functions are used to extract and normalize data from raw scraped content.
The normalization module is used for enum-based normalization.
"""

import re

from src.core.enums import City, Currency, OfferType, PropertyType
from src.core.normalization import (
    normalize_agency,
    normalize_city,
    normalize_currency,
    normalize_neighborhood,
    normalize_offer_type,
    normalize_property_type,
)


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
    result = normalize_currency(text)
    return result.value if isinstance(result, Currency) else result


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
    result = normalize_city(location)
    return result.value if isinstance(result, City) else result


def extract_neighborhood(location: str, city: str = "") -> str:
    """
    Extract and normalize neighborhood from location string.

    Args:
        location: Location string like "гр. София, Лозенец"
        city: Optional city for context-aware normalization

    Returns:
        Normalized neighborhood name
    """
    if not location:
        return ""
    parts = location.split(",")
    neighborhood = parts[1].strip() if len(parts) > 1 else ""
    if not neighborhood:
        return ""
    result = normalize_neighborhood(neighborhood, city)
    if hasattr(result, "value"):
        return result.value
    return result


def extract_property_type(text: str, url: str = "") -> str:
    """
    Extract and normalize property type from text and/or URL.

    Args:
        text: Text content (e.g., title) to search
        url: URL to search for patterns

    Returns:
        Normalized property type string
    """
    result = normalize_property_type(text, url)
    return result.value if isinstance(result, PropertyType) else result


def extract_offer_type(text: str, url: str = "") -> str:
    """
    Extract and normalize offer type from text and/or URL.

    Args:
        text: Text content (e.g., title) to search
        url: URL to search for patterns

    Returns:
        Normalized offer type string (продава or наем)
    """
    result = normalize_offer_type(text, url)
    return result.value if isinstance(result, OfferType) else result


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
