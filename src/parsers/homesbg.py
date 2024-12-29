from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, HttpUrl, ValidationError

from src.logger_setup import get_logger
from src.models import PropertyType, Site

logger = get_logger(__name__)


def clean_price(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        cleaned_value = value.split()[0].replace(",", "")  # Remove commas and take the numeric part
        return float(cleaned_value)
    except ValueError:
        logger.error(f"Failed to clean price value: {value}")
        return None


class RawHomesBgListingData(BaseModel):
    id: Optional[str]
    type: Optional[str]
    url: Optional[HttpUrl]
    title: Optional[str]
    location: Optional[str]
    description: Optional[str]
    price_value: Optional[float]
    price_currency: Optional[str]
    main_photo: Optional[HttpUrl]
    photos: Optional[List[HttpUrl]]
    is_favorite: Optional[bool]
    date_added: Optional[datetime] = None
    floor: Optional[str] = ""
    price_per_square_meter: Optional[str] = ""
    offer_type: Optional[str] = ""
    property_type: Optional[PropertyType] = PropertyType.UNKNOWN


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

    def __init__(self):
        pass

    def map_offer_type(self, search_type: str) -> str:
        if "ApartmentRent" in search_type:
            return "под наем"
        elif "ApartmentSell" in search_type:
            return "продажба"

    def extract_listing_data(
        self,
        listing: Dict,
        search_criteria: dict = {},
    ) -> RawHomesBgListingData:
        try:
            if search_criteria:
                offer_type = self.map_offer_type(search_criteria)
            else:
                offer_type = ""
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
                "main_photo": main_photo_url,
                "photos": photos_urls,
                "is_favorite": listing.get(self.IS_FAVORITE_KEY, False),
            }

            return RawHomesBgListingData(**data)
        except ValidationError as ve:
            logger.error(f"Validation error for listing data: {ve}")
            return RawHomesBgListingData()
        except Exception as e:
            logger.error(f"Error extracting listing data: {e}", exc_info=True)
            return RawHomesBgListingData()

    def parse_listings(self, data: Dict) -> List[RawHomesBgListingData]:
        try:
            search_criteria = data.get("searchCriteria", {})
            raw_listings = data.get(self.RESULT_KEY, [])
            listings = [self.extract_listing_data(listing, search_criteria) for listing in raw_listings]
            logger.info(f"Parsed {len(listings)} listings from data.")
            return listings
        except Exception as e:
            logger.error(f"Error parsing listings: {e}", exc_info=True)
            return []

    @classmethod
    def convert_property_type(cls, property_type: str) -> PropertyType:
        print("property_type = ", property_type)
        type_mapping = {
            "Едностаен": PropertyType.EDNOSTAEN,
            "Двустаен": PropertyType.DVUSTAEN,
            "тристаен": PropertyType.TRISTAEN,
            "четиристаен": PropertyType.CHETIRISTAEN,
            "мезонет": PropertyType.MESONET,
        }
        return type_mapping.get(property_type.lower(), PropertyType.UNKNOWN)

    @classmethod
    def to_property_listing_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        try:
            # Ensure required columns exist, fill missing ones with default values
            if "agency" not in df.columns:
                df["agency"] = None  # Fill missing 'agency' column with None

            # Normalize column names
            df["title"] = df["title"]
            df["price"] = df["price_value"].fillna(0).astype(int, errors="ignore")
            df["currency"] = df["price_currency"].fillna("unknown")

            df["offer_type"] = df["offer_type"]
            df["property_type"] = df["property_type"]

            df["city"] = df["location"].str.split(",").str[0].str.strip()
            df["neighborhood"] = df["location"].str.split(",").str[1].str.strip()

            # Map remaining fields
            df["description"] = df["description"]
            df["contact_info"] = None  # Homes.bg does not provide contact info directly
            df["agency_url"] = None  # Homes.bg does not provide agency URLs
            df["details_url"] = df["url"]
            df["num_photos"] = df["photos"].apply(lambda x: len(x) if isinstance(x, list) else 0)
            df["date_added"] = df["date_added"]
            df["site"] = Site.HOMESBG
            df["floor"] = df["floor"]
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
            logger.error(f"Error converting Homes.bg data to PropertyListingData: {e}", exc_info=True)
            return pd.DataFrame()
