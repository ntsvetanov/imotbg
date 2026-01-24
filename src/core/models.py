from datetime import datetime

from pydantic import BaseModel, Field


class ListingData(BaseModel):
    """Normalized property listing data model."""

    raw_title: str = Field(default="")
    raw_description: str = Field(default="")
    price: float = Field(default=0.0)
    currency: str = Field(default="")
    without_dds: bool = Field(default=False)
    offer_type: str = Field(default="")
    property_type: str = Field(default="")
    city: str = Field(default="")
    neighborhood: str = Field(default="")
    contact_info: str = Field(default="")
    agency: str = Field(default="")
    agency_url: str = Field(default="")
    details_url: str = Field(default="")
    num_photos: int = Field(default=0)
    date_time_added: datetime | None = Field(default=None)
    search_url: str = Field(default="")
    site: str = Field(default="")
    total_offers: int = Field(default=0)
    ref_no: str = Field(default="")
    time: str = Field(default="")
    price_per_m2: str = Field(default="")
    area: str = Field(default="")
    floor: str = Field(default="")
