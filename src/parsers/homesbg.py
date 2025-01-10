from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from src.logger_setup import get_logger
from src.models import PropertyType, Site

logger = get_logger(__name__)


def clean_price(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        cleaned_value = value.split()[0].replace(",", "")
        return float(cleaned_value)
    except ValueError:
        logger.error(f"Failed to clean price value: {value}", exc_info=True)
        return None


class RawHomesBgListingData(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the listing.")
    type: Optional[str] = Field(None, description="Type of listing (e.g., 'rent', 'sale').")
    url: Optional[str] = Field(None, description="URL to the listing.")
    time: Optional[str] = Field("", description="Time of listing update.")
    location: Optional[str] = Field(None, description="Location of the property.")
    title: Optional[str] = Field(None, description="Title of the listing.")
    description: Optional[str] = Field(None, description="Description of the property.")
    status: int = Field(0, description="Status of the listing (e.g., active/inactive).")
    photos: List[str] = Field(default_factory=list, description="List of photo URLs.")
    price_value: Optional[float] = Field(None, description="Price of the property.")
    price_currency: Optional[str] = Field(None, description="Currency of the price.")
    price_per_square_meter: str = Field("", description="Price per square meter.")
    price_period: Optional[str] = Field("", description="Price period (e.g., monthly, yearly).")
    main_photo: Optional[str] = Field(None, description="URL of the main photo.")
    is_favorite: Optional[bool] = Field(None, description="Whether the listing is marked as favorite.")
    offer_type: str = Field("", description="Offer type of the property.")
    property_type: PropertyType = Field(PropertyType.UNKNOWN, description="Type of the property.")
    date_added: Optional[datetime] = Field(None, description="Date when the listing was added.")
    search_url: str = Field("", description="URL used for search related to this listing.")
    total_offers: int = Field(0, description="Total number of offers related to this listing.")
    location_id: str = Field("", description="Identifier for the location.")
    neighborhoods: List[str] = Field(
        default_factory=list, description="List of neighborhoods associated with the location."
    )
    main_property_type: Optional[str] = Field("", description="Main property type of the listing.")

    class Config:
        schema_extra = {
            "example": {
                "id": "12345",
                "type": "rent",
                "url": "https://example.com/listing/12345",
                "time": "2025-01-01T12:00:00Z",
                "location": "Downtown",
                "title": "Spacious 2-bedroom Apartment",
                "description": "A beautiful 2-bedroom apartment located in the heart of the city.",
                "status": 1,
                "photos": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
                "price_value": 1200.0,
                "price_currency": "USD",
                "price_per_square_meter": "15.0",
                "price_period": "monthly",
                "main_photo": "https://example.com/main_photo.jpg",
                "is_favorite": True,
                "offer_type": "rent",
                "property_type": "apartment",
                "date_added": "2025-01-01T12:00:00Z",
                "search_url": "https://example.com/search?query=apartment",
                "total_offers": 5,
                "location_id": "loc_001",
                "neighborhoods": ["Downtown", "Central Park"],
            }
        }


class HomesBgParser:
    BASE_URL = "https://homes.bg"
    PHOTO_PATH_KEY = "path"
    PHOTO_NAME_KEY = "name"
    PRICE_KEY = "price"
    PRICE_VALUE_KEY = "value"
    PRICE_CURRENCY_KEY = "currency"
    PRICE_PER_SQUARE_METER_KEY = "price_per_square_meter"
    VIEW_HREF_KEY = "viewHref"
    ID_KEY = "id"
    TYPE_KEY = "type"
    TITLE_KEY = "title"
    LOCATION_KEY = "location"
    DESCRIPTION_KEY = "description"
    IS_FAVORITE_KEY = "isFav"
    RESULT_KEY = "result"
    TIME_KEY = "time"
    STATUS_KEY = "status"
    PRICE_PERIOD_KEY = "period"

    def map_offer_type(self, search_type: str) -> str:
        if "ApartmentRent" in search_type:
            return "апартамент, под наем"
        elif "ApartmentSell" in search_type:
            return "апартамент, продажба"
        elif "LandAgro" in search_type:
            return "земеделска земя, продажба"
        elif "HouseSell" in search_type:
            return "къща, продажба"
        elif "HouseRent" in search_type:
            return "къща, под наем"
        return ""

    def extract_listing_data(
        self,
        listing: Dict,
        search_criteria: dict = {},
        search_url: str = "",
        total_offers: int = 0,
    ) -> RawHomesBgListingData:
        try:
            offer_type = ""
            main_property_type = ""

            if search_criteria:
                raw_offer_type = self.map_offer_type(search_criteria)
                if raw_offer_type:
                    main_property_type = raw_offer_type.split(",")[1]
                    offer_type = raw_offer_type.split(",")[0]
            total_offers = total_offers
            location_id = search_criteria.get("locationId", "")
            neighborhoods = search_criteria.get("neighbourhoods", [])

            title = listing.get(self.TITLE_KEY)

            property_type = self.convert_property_type(title.split(",")[0].strip())

            photo = listing.get(self.PHOTO_PATH_KEY, {})
            main_photo_url = (
                f"{self.BASE_URL}/{photo.get(self.PHOTO_PATH_KEY, '')}{photo.get(self.PHOTO_NAME_KEY, '')}"
                if photo
                else None
            )

            photos_urls = [
                f"{self.BASE_URL}/{photo.get(self.PHOTO_PATH_KEY, '')}{photo.get(self.PHOTO_NAME_KEY, '')}"
                for photo in listing.get("photos", [])
            ]

            data = {
                "id": listing.get(self.ID_KEY),
                "type": listing.get(self.TYPE_KEY),
                "url": f"{self.BASE_URL}{listing.get(self.VIEW_HREF_KEY, '')}",
                "offer_type": offer_type,
                "property_type": property_type,
                "title": title,
                "location": listing.get(self.LOCATION_KEY),
                "description": listing.get(self.DESCRIPTION_KEY),
                "price_value": clean_price(listing.get(self.PRICE_KEY, {}).get(self.PRICE_VALUE_KEY)),
                "price_currency": listing.get(self.PRICE_KEY, {}).get(self.PRICE_CURRENCY_KEY),
                "price_per_square_meter": listing.get(self.PRICE_KEY, {}).get(self.PRICE_PER_SQUARE_METER_KEY),
                "price_period": listing.get(self.PRICE_KEY, {}).get(self.PRICE_PERIOD_KEY),
                "main_photo": main_photo_url,
                "photos": photos_urls,
                "is_favorite": listing.get(self.IS_FAVORITE_KEY, False),
                "date_added": datetime.now(),
                "search_url": search_url,
                "time": listing.get(self.TIME_KEY),
                "status": listing.get(self.STATUS_KEY),
                "total_offers": total_offers,
                "location_id": location_id,
                "neighborhoods": neighborhoods,
                "main_property_type": main_property_type,
            }

            return RawHomesBgListingData(**data)
        except ValidationError as ve:
            logger.error(f"Validation error for listing data: {ve}", exc_info=True)
            return RawHomesBgListingData()
        except Exception as e:
            logger.error(f"Error extracting listing data: {e}", exc_info=True)
            return RawHomesBgListingData()

    def parse_listings(
        self,
        data: Dict,
        url: str,
    ) -> List[RawHomesBgListingData]:
        try:
            total_offers = data.get("offersCount", 0)
            search_criteria = data.get("searchCriteria", {})
            raw_listings = data.get(self.RESULT_KEY, [])
            listings = [
                self.extract_listing_data(
                    listing,
                    search_criteria,
                    url,
                    total_offers,
                )
                for listing in raw_listings
            ]
            logger.info(f"Parsed {len(listings)} listings from data.")
            return listings
        except Exception as e:
            logger.error(f"Error parsing listings: {e}", exc_info=True)
            return []

    @classmethod
    def convert_property_type(cls, property_type: str) -> PropertyType:
        type_mapping = {
            "едностаен": PropertyType.EDNOSTAEN,
            "двустаен": PropertyType.DVUSTAEN,
            "тристаен": PropertyType.TRISTAEN,
            "четиристаен": PropertyType.CHETIRISTAEN,
            "мезонет": PropertyType.MESONET,
            "многостаен": PropertyType.MNOGOSTAEN,
        }
        return type_mapping.get(
            property_type.lower(),
            PropertyType.UNKNOWN,
        )

    @classmethod
    def to_property_listing_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        try:
            if "agency" not in df.columns:
                df["agency"] = None

            df["title"] = df["title"]
            df["price"] = df["price_value"].fillna(0).astype(int, errors="ignore")
            df["currency"] = df["price_currency"].fillna("unknown")

            df["offer_type"] = df["offer_type"]
            df["property_type"] = df["property_type"]

            df["city"] = df["location"].str.split(",").str[0].str.strip()
            df["neighborhood"] = df["location"].str.split(",").str[1].str.strip()

            df["description"] = df["description"]
            df["contact_info"] = None  # Homes.bg does not provide contact info directly
            df["agency_url"] = None  # Homes.bg does not provide agency URLs
            df["details_url"] = df["url"]
            df["num_photos"] = df["photos"].apply(lambda x: len(x) if isinstance(x, list) else 0)
            df["date_added"] = df["date_added"]
            df["site"] = Site.HOMESBG
            df["floor"] = None
            df["price_per_m2"] = df["price_per_square_meter"]
            df["ref_no"] = df["id"]
            df["area"] = None  # Homes.bg does not explicitly provide area info
            df["date_added"] = datetime.now().isoformat()
            return df[
                [
                    "title",
                    "price",
                    "currency",
                    "offer_type",
                    "property_type",
                    "city",
                    "neighborhood",
                    "description",
                    "contact_info",
                    "agency",
                    "agency_url",
                    "details_url",
                    "num_photos",
                    "date_added",
                    "site",
                    "floor",
                    "price_per_m2",
                    "ref_no",
                    "area",
                ]
            ]
        except Exception as e:
            logger.error(
                f"Error converting Homes.bg data to PropertyListingData: {e}",
                exc_info=True,
            )
            return pd.DataFrame()
