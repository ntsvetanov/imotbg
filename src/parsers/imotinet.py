from datetime import datetime
from typing import List, Optional

from bs4 import Tag

from src.logger_setup import get_logger
from src.utils import get_text_or_none, parse_soup

logger = get_logger(__name__)

from pydantic import BaseModel


class RawImotiNetListingData(BaseModel):
    title: Optional[str]
    price_and_currency: Optional[str]
    location: Optional[str]
    details_url: Optional[str]
    agency: Optional[str]
    floor: Optional[str]
    price_per_m2: Optional[str]
    description: Optional[str]
    reference_number: Optional[str]
    is_top_ad: bool
    num_photos: Optional[str]
    date_added: Optional[datetime] = None


class ImotiNetParser:
    LISTING_CLASS = "clearfix"
    IMAGE_TAG = "img"
    BOX_LINK_CLASS = "box-link"
    PRICE_CLASS = "price"
    LOCATION_CLASS = "location"
    AGENCY_CLASS = "re-offer-type"
    FLAG_TOP_CLASS = "flag flag-top absolute"
    PIC_VIDEO_INFO_CLASS = "pic-video-info-number"
    PAGINATOR_CLASS = "paginator"
    LAST_PAGE_CLASS = "last-page"
    REFERENCE_NUMBER_KEY = "Референтен номер:"
    FLOOR_KEY = "Етаж:"
    PRICE_PER_M2_KEY = "Цена на /м"

    BASE_URL = "https://www.imoti.net"

    def __init__(self):
        self.soup = None

    def extract_listing_data(self, listing: Tag) -> RawImotiNetListingData:
        try:
            # Extract image URL
            image_tag = listing.find(self.IMAGE_TAG)
            image_url = image_tag.get("src", None) if image_tag else None

            # Extract details URL
            details_link_tag = listing.find("a", {"class": self.BOX_LINK_CLASS})
            details_url = details_link_tag.get("href", None) if details_link_tag else None

            # Extract reference number and description
            description_paragraphs = listing.find_all("p")
            reference_number = None
            description = None
            for paragraph in description_paragraphs:
                text = paragraph.get_text(strip=True)
                if self.REFERENCE_NUMBER_KEY in text:
                    reference_number = text.split(self.REFERENCE_NUMBER_KEY)[-1].strip()
                elif not description:
                    description = text

            # Populate data dictionary
            data = {
                "title": get_text_or_none(listing, ("h3", {})),
                "price_and_currency": get_text_or_none(listing, ("strong", {"class": self.PRICE_CLASS})),
                "location": get_text_or_none(listing, ("span", {"class": self.LOCATION_CLASS})),
                "details_url": details_url,
                "num_photos": get_text_or_none(listing, ("span", {"class": self.PIC_VIDEO_INFO_CLASS})),
                "agency": get_text_or_none(listing, ("span", {"class": self.AGENCY_CLASS})),
                "floor": get_text_or_none(listing, ("li", {"text": lambda t: t and self.FLOOR_KEY in t})),
                "price_per_m2": get_text_or_none(listing, ("li", {"text": lambda t: t and self.PRICE_PER_M2_KEY in t})),
                "description": description,
                "reference_number": reference_number,
                "is_top_ad": bool(listing.find("span", {"class": self.FLAG_TOP_CLASS})),
            }

            # Add base URL to relative paths
            if data["details_url"] and not data["details_url"].startswith("http"):
                data["details_url"] = f"{self.BASE_URL}{data['details_url']}"
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.BASE_URL}{image_url}"

            # Include the image URL in the data
            data["image_url"] = image_url

            data["data_added"] = datetime.now().isoformat()

            # Return the parsed data as a Pydantic model
            return RawImotiNetListingData(**data)

        except Exception as e:
            logger.error(f"Error extracting listing data: {e}", exc_info=True)
            return RawImotiNetListingData(
                title=None,
                price=None,
                location=None,
                details_url=None,
                agency=None,
                floor=None,
                price_per_m2=None,
                description=None,
                reference_number=None,
                is_top_ad=False,
                num_photos=None,
            )

    def parse_listings(self, page_content: str) -> List[RawImotiNetListingData]:
        try:
            soup = parse_soup(page_content)
            listings = soup.find_all("li", {"class": self.LISTING_CLASS})
            return [self.extract_listing_data(listing) for listing in listings]
        except Exception as e:
            logger.error(f"Error parsing listings: {e}", exc_info=True)
            return []

    def get_total_pages(self, page_content: str) -> int:
        try:
            soup = parse_soup(page_content)
            paginator = soup.find("nav", {"class": self.PAGINATOR_CLASS})

            if paginator:
                last_page_link = paginator.find("a", {"class": self.LAST_PAGE_CLASS})
                if last_page_link:
                    return int(last_page_link.text.strip())

            return 1
        except Exception as e:
            logger.error(f"Error extracting total pages: {e}", exc_info=True)
            return 1
