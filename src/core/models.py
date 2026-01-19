from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ListingData(BaseModel):
    raw_title: Optional[str] = Field(default="")
    raw_description: Optional[str] = Field(default="")
    price: Optional[float] = Field(default=0.0)
    currency: Optional[str] = Field(default="")
    without_dds: Optional[bool] = Field(default=False)
    offer_type: Optional[str] = Field(default="")
    property_type: Optional[str] = Field(default="")
    city: Optional[str] = Field(default="")
    neighborhood: Optional[str] = Field(default="")
    contact_info: Optional[str] = Field(default="")
    agency: Optional[str] = Field(default="")
    agency_url: Optional[str] = Field(default="")
    details_url: Optional[str] = Field(default="")
    num_photos: Optional[int] = Field(default=0)
    date_time_added: Optional[datetime] = Field(default=None)
    search_url: Optional[str] = Field(default="")
    site: Optional[str] = Field(default="")
    total_offers: Optional[int] = Field(default=0)
    ref_no: Optional[str] = Field(default="")
    time: Optional[str] = Field(default="")
    price_per_m2: Optional[str] = Field(default="")
    area: Optional[str] = Field(default="")
    floor: Optional[str] = Field(default="")
