"""
Data models for property listings.

This module defines the core ListingData model with support for
enum-based fields and duplicate detection via fingerprinting.
"""

import hashlib
from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field, computed_field

from src.core.enums import (
    City,
    Currency,
    OfferType,
    PlovdivNeighborhood,
    PropertyType,
    SofiaNeighborhood,
)

# Type aliases for fields that can be enum or string (soft validation)
OfferTypeField = Union[OfferType, str]
PropertyTypeField = Union[PropertyType, str]
CityField = Union[City, str]
NeighborhoodField = Union[SofiaNeighborhood, PlovdivNeighborhood, str]
CurrencyField = Union[Currency, str]


class ListingData(BaseModel):
    """
    Normalized property listing data model.

    Supports both enum values and strings for flexible validation.
    Enum values are serialized as their string values for backward compatibility.
    """

    raw_title: str = Field(default="")
    raw_description: str | None = Field(default=None)
    price: float | None = Field(default=None)
    currency: CurrencyField = Field(default="")
    without_dds: bool = Field(default=False)
    offer_type: OfferTypeField = Field(default="")
    property_type: PropertyTypeField = Field(default="")
    city: CityField = Field(default="")
    neighborhood: NeighborhoodField = Field(default="")
    contact_info: str | None = Field(default=None)
    agency: str | None = Field(default=None)
    agency_url: str | None = Field(default=None)
    details_url: str = Field(default="")
    num_photos: int | None = Field(default=None)
    date_time_added: datetime | None = Field(default=None)
    search_url: str | None = Field(default=None)
    site: str = Field(default="")
    total_offers: int | None = Field(default=None)
    ref_no: str = Field(default="")
    time: str = Field(default="")
    price_per_m2: str | None = Field(default=None)
    area: str | None = Field(default=None)
    floor: str | None = Field(default=None)

    @computed_field
    @property
    def fingerprint_hash(self) -> str:
        """
        Compute MD5 hash of the fingerprint for efficient storage and comparison.

        Returns:
            MD5 hex digest of the fingerprint string.
        """
        fp = self.fingerprint()
        return hashlib.md5(fp.encode()).hexdigest()

    def _get_value(self, field_value) -> str:
        """Extract string value from enum or string."""
        if hasattr(field_value, "value"):
            return field_value.value
        return str(field_value) if field_value else ""

    def fingerprint(self) -> str:
        """
        Generate a fingerprint for duplicate detection.
        Based on: price + area + property_type + city

        The fingerprint uses normalized values with some tolerance:
        - Price is rounded to nearest 100 for fuzzy matching
        - Area is rounded to integer

        Returns:
            A string fingerprint that can be compared across sites.
        """
        # Normalize property_type to string value
        prop_type = self._get_value(self.property_type)

        # Normalize city to string value
        city_val = self._get_value(self.city)

        # Normalize area (remove decimals for fuzzy matching)
        area_normalized = ""
        if self.area:
            try:
                area_normalized = str(int(float(self.area)))
            except (ValueError, TypeError):
                area_normalized = str(self.area)

        # Normalize price (round to nearest 100 for fuzzy matching)
        price_normalized = ""
        if self.price:
            price_normalized = str(int(round(self.price / 100) * 100))

        return f"{price_normalized}|{area_normalized}|{prop_type}|{city_val}"

    def fingerprint_strict(self) -> str:
        """
        Stricter fingerprint including neighborhood.
        Use this when you want to match offers in the same neighborhood.

        Returns:
            A string fingerprint with neighborhood included.
        """
        base = self.fingerprint()
        neighborhood_val = self._get_value(self.neighborhood)
        return f"{base}|{neighborhood_val}"

    def fingerprint_loose(self) -> str:
        """
        Looser fingerprint for broader matching.
        Based on: price (rounded to 500) + property_type + city

        Returns:
            A string fingerprint with less precision.
        """
        prop_type = self._get_value(self.property_type)
        city_val = self._get_value(self.city)

        # Round price to nearest 500
        price_normalized = ""
        if self.price:
            price_normalized = str(int(round(self.price / 500) * 500))

        return f"{price_normalized}|{prop_type}|{city_val}"

    def matches(self, other: "ListingData", strict: bool = False) -> bool:
        """
        Check if this listing potentially matches another listing.

        Args:
            other: Another ListingData to compare with
            strict: If True, use strict fingerprint (includes neighborhood)

        Returns:
            True if fingerprints match
        """
        if strict:
            return self.fingerprint_strict() == other.fingerprint_strict()
        return self.fingerprint() == other.fingerprint()

    class Config:
        """Pydantic model configuration."""

        # Serialize enums by their value
        use_enum_values = True
