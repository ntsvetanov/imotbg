from typing import Dict, List

from src.logger_setup import get_logger

logger = get_logger(__name__)


class HomesbgParser:
    def extract_listing_data(self, listing: Dict) -> Dict:
        try:
            # Extract the main photo details
            photo = listing.get("photo", {})
            photo_url = f"https://homes.bg/{photo.get('path', '')}{photo.get('name', '')}" if photo else None

            # Extract listing details
            data = {
                "id": listing.get("id"),
                "type": listing.get("type"),
                "url": f"https://homes.bg{listing.get('viewHref', '')}",
                "title": listing.get("title"),
                "location": listing.get("location"),
                "description": listing.get("description"),
                "price": {
                    "value": listing.get("price", {}).get("value"),
                    "currency": listing.get("price", {}).get("currency"),
                    "price_per_square_meter": listing.get("price", {}).get("price_per_square_meter"),
                },
                "photos": [
                    f"https://homes.bg/{photo.get('path', '')}{photo.get('name', '')}"
                    for photo in listing.get("photos", [])
                ],
                "main_photo": photo_url,
                "is_favorite": listing.get("isFav", False),
            }

            return data
        except Exception as e:
            logger.error(f"Error extracting listing data: {e}", exc_info=True)
            return {}

    def parse_listings(self, data: Dict) -> List[Dict]:
        try:
            return [self.extract_listing_data(listing) for listing in data.get("result", [])]
        except Exception as e:
            logger.error(f"Error parsing listings: {e}", exc_info=True)
            return []
