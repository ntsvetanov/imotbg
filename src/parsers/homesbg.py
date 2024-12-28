from typing import Dict, List, Optional

from pydantic import BaseModel, HttpUrl, ValidationError

from src.logger_setup import get_logger

logger = get_logger(__name__)


def clean_price(value: Optional[str]) -> Optional[float]:
    """
    Cleans and converts a price string into a float.
    Removes commas and extraneous text like currency symbols.
    """
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
    price_per_square_meter: Optional[float]
    main_photo: Optional[HttpUrl]
    photos: Optional[List[HttpUrl]]
    is_favorite: Optional[bool]


class HomesbgParser:
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

    def extract_listing_data(self, listing: Dict) -> RawHomesBgListingData:
        try:
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
                "title": listing.get(self.TITLE_KEY),
                "location": listing.get(self.LOCATION_KEY),
                "description": listing.get(self.DESCRIPTION_KEY),
                "price_value": clean_price(listing.get(self.PRICE_KEY, {}).get(self.PRICE_VALUE_KEY)),
                "price_currency": listing.get(self.PRICE_KEY, {}).get(self.PRICE_CURRENCY_KEY),
                "price_per_square_meter": clean_price(
                    listing.get(self.PRICE_KEY, {}).get(self.PRICE_PER_SQUARE_METER_KEY)
                ),
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
            raw_listings = data.get(self.RESULT_KEY, [])
            listings = [self.extract_listing_data(listing) for listing in raw_listings]
            logger.info(f"Parsed {len(listings)} listings from data.")
            return listings
        except Exception as e:
            logger.error(f"Error parsing listings: {e}", exc_info=True)
            return []
