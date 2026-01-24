from datetime import datetime

from pydantic import BaseModel, Field


class ListingData(BaseModel):
    """Normalized property listing data model."""

    raw_title: str = Field(default="")
    raw_description: str | None = Field(default=None)
    price: float | None = Field(default=None)
    currency: str = Field(default="")
    without_dds: bool = Field(default=False)
    offer_type: str = Field(default="")
    property_type: str = Field(default="")
    city: str = Field(default="")
    neighborhood: str = Field(default="")
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
