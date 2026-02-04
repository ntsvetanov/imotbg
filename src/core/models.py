"""
Data models for property listings.

This module defines:
- RawListing: Unified schema for extracted data from all sites
- ListingData: Normalized data model with prices in EUR
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RawListing(BaseModel):
    """
    Raw extracted data - unified schema for all sites.

    All extractors must output data in this format.
    All fields except 'site' are optional to handle partial data.
    """

    # Required - must always know the source
    site: str

    # Metadata
    search_url: str | None = Field(default=None)
    scraped_at: datetime | None = Field(default=None)

    # URLs
    details_url: str | None = Field(default=None)
    agency_url: str | None = Field(default=None)

    # Price (raw text - will be parsed by Transformer)
    price_text: str | None = Field(default=None)

    # Location (raw text - will be parsed by Transformer)
    location_text: str | None = Field(default=None)

    # Property info
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    area_text: str | None = Field(default=None)
    floor_text: str | None = Field(default=None)
    total_floors_text: str | None = Field(default=None)

    # Agency
    agency_name: str | None = Field(default=None)

    # Other
    num_photos: int | None = Field(default=None)
    ref_no: str | None = Field(default=None)
    total_offers: int | None = Field(default=None)
    raw_link_description: str | None = Field(default=None)


class ListingData(BaseModel):
    """
    Normalized property listing data.

    Output of the Transformer with:
    - Prices always in EUR
    - Normalized city/neighborhood names
    - Normalized property/offer types
    - Computed fields (price_per_m2, fingerprint_hash)
    """

    # Source tracking
    site: str
    search_url: str | None = Field(default=None)
    details_url: str = Field(default="")

    # Price (always EUR)
    price: float | None = Field(default=None)
    original_currency: str = Field(default="")
    price_per_m2: float | None = Field(default=None)

    # Location (normalized)
    city: str = Field(default="")
    neighborhood: str = Field(default="")

    # Property (normalized)
    offer_type: str = Field(default="")
    property_type: str = Field(default="")

    # Details
    area: float | None = Field(default=None)
    floor: str | None = Field(default=None)
    total_floors: str | None = Field(default=None)

    # Raw content preserved
    raw_title: str = Field(default="")
    raw_description: str | None = Field(default=None)

    # Agency
    agency: str | None = Field(default=None)
    agency_url: str | None = Field(default=None)

    # Other
    num_photos: int | None = Field(default=None)
    ref_no: str = Field(default="")
    date_time_added: datetime | None = Field(default=None)
    total_offers: int | None = Field(default=None)

    # Computed - set by Transformer
    fingerprint_hash: str = Field(default="")

    def fingerprint(self) -> str:
        """
        Generate a fingerprint for duplicate detection.
        Based on: price (rounded to 100) + area (integer) + property_type + city
        """
        price_norm = ""
        if self.price:
            price_norm = str(int(round(self.price / 100) * 100))

        area_norm = ""
        if self.area:
            area_norm = str(int(self.area))

        return f"{price_norm}|{area_norm}|{self.property_type}|{self.city}"

    def matches(self, other: "ListingData") -> bool:
        """Check if this listing potentially matches another (same fingerprint)."""
        return self.fingerprint() == other.fingerprint()

    model_config = ConfigDict(use_enum_values=True)
