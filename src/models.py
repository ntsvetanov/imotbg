import enum
from datetime import datetime
from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, HttpUrl, ValidationError, validator

from src.logger_setup import get_logger

logger = get_logger(__name__)


class Site(enum.Enum):
    IMOTBG = "imot.bg"
    IMOTINET = "imoti.net"
    HOMESBG = "homes.bg"


class PropertyType(enum.Enum):
    UNKNOWN = ""
    EDNOSTAEN = "едностаен"
    DVUSTAEN = "двустаен"
    TRISTAEN = "тристаен"
    CHETIRISTAEN = "четиристаен"
    MESONET = "мезонет"
    MNOGOSTAEN = "многостаен"


class PropertyListingData(BaseModel):
    title: Optional[str] = ""

    price: Optional[int] = 0
    currency: Optional[str] = ""

    offer_type: Optional[str] = ""
    property_type: Optional[PropertyType] = PropertyType.UNKNOWN

    city: Optional[str] = ""
    neighborhood: Optional[str] = ""

    description: Optional[str] = ""
    contact_info: Optional[str] = ""
    agency: Optional[str] = ""
    agency_url: Optional[HttpUrl] = None
    details_url: Optional[HttpUrl] = None
    num_photos: Optional[int] = 0
    date_added: Optional[datetime] = None
    site: Site
    floor: Optional[str] = ""
    price_per_m2: Optional[str] = ""
    ref_no: Optional[str] = ""
    area: Optional[str] = ""
    model_config = ConfigDict(use_enum_values=True)

    @validator("price", pre=True)
    def validate_price(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return 0
        return int(value) if isinstance(value, (int, str)) else value

    @validator("currency", pre=True)
    def validate_currency(cls, value):
        if value is None or (isinstance(value, float) and value != value):
            return "unknown"
        return str(value)

    @classmethod
    def to_property_listing(cls, df):
        valid_rows = []

        for _, row in df.iterrows():
            try:
                validated_data = cls(**row.to_dict())
                valid_rows.append(validated_data.model_dump())
            except ValidationError:
                logger.error(f"Invalid row: {row.to_dict()}", exc_info=True)

        valid_df = pd.DataFrame(valid_rows)
        return valid_df
