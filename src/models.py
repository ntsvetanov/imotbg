import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.logger_setup import get_logger

logger = get_logger(__name__)


class ListingSite(enum.Enum):
    IMOTI_NET = "imoti.net"
    HOMES_BG = "homes.bg"
    IMOT_BG = "imot.bg"


class Currency(enum.Enum):
    BGN = "BGN"
    EUR = "EUR"


class OfferType(enum.Enum):
    SELL = "продава"
    RENT = "наем"


class PropertyType(enum.Enum):
    EDNOSTAEN = "едностаен"
    DVUSTAEN = "двустаен"
    TRISTAEN = "тристаен"
    CHETIRISTAEN = "четиристаен"
    MEZONET = "мезонет"
    MNOGOSTAEN = "многостаен"
    LAND = "земя"


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
    num_photos: Optional[float] = Field(default=0)
    date_time_added: Optional[datetime] = Field(default=None)
    search_url: Optional[str] = Field(default="")
    site: Optional[str] = Field(default="")
    total_offers: Optional[int] = Field(default=0)
    date: Optional[datetime] = Field(default=None)
    ref_no: Optional[str] = Field(default="")
    time: Optional[str] = Field(default="")
    price_per_m2: Optional[str] = Field(default="")
    area: Optional[str] = Field(default="")
    floor: Optional[str] = Field(default="")


class PropertyListingData:
    pass


# class ListingData(BaseModel):
#     raw_title: Optional[str] = Field("")
#     raw_description: Optional[str] = Field("")

#     price: Optional[float] = Field(0.0)
#     currency: Optional[str] = Field("")

#     offer_type: Optional[str] = Field("")
#     property_type: Optional[str] = Field("")

#     city: Optional[str] = Field("")
#     neighborhood: Optional[str] = Field("")
#     contact_info: Optional[str] = Field("")
#     agency: Optional[str] = Field("")
#     agency_url: Optional[str] = Field("")

#     details_url: Optional[str] = Field("")
#     num_photos: Optional[int] = Field(0)
#     date_added: Optional[str] = Field("")
#     search_url: Optional[str] = Field("")
#     site: Optional[str] = Field("")
#     total_offers: Optional[int] = Field(0)

#     ref_no = Optional[str] = Field("")
#     time = Optional[str] = Field("") # homes bg only
#     price_per_m2 = Optional[str] = Field("") # homes bg only
#     area = Optional[str] = Field("") # imoti net only
#     floor = Optional[str] = Field("") # imoti net only

#     model_config = ConfigDict(use_enum_values=False)

#     @validator("price", pre=True)
#     def validate_price(cls, value):
#         if isinstance(value, str) and value.strip() == "":
#             return 0
#         return float(value) if isinstance(value, (float, int, str)) else value

#     @validator("currency", pre=True)
#     def validate_currency(cls, value):
#         if value is None or (isinstance(value, float) and value != value):
#             return "unknown"
#         return str(value)

#     @classmethod
#     def to_property_listing(cls, df):
#         valid_rows = []

#         for _, row in df.iterrows():
#             try:
#                 validated_data = cls(**row.to_dict())
#                 valid_rows.append(validated_data.model_dump())
#             except ValidationError:
#                 logger.error(f"Invalid row: {row.to_dict()}", exc_info=True)

#         valid_df = pd.DataFrame(valid_rows)
#         return valid_df
