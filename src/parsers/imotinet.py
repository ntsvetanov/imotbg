from datetime import datetime
from typing import List, Optional

from bs4 import Tag

from src.logger_setup import get_logger
from src.models import PropertyType, Site
from src.utils import get_text_or_none, parse_soup, validate_url

logger = get_logger(__name__)

from pydantic import BaseModel


class RawImotiNetListingData(BaseModel):
    title: Optional[str]
    price_and_currency: Optional[str]
    location: Optional[str]
    details_url: Optional[str]
    property_type: Optional[str]
    area: Optional[str]
    agency: Optional[str]
    agency_url: Optional[str]
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

    def extract_listing_data(self, listing: Tag) -> RawImotiNetListingData:
        try:
            image_tag = listing.find(self.IMAGE_TAG)
            image_url = image_tag.get("src", None) if image_tag else None

            details_link_tag = listing.find("a", {"class": self.BOX_LINK_CLASS})
            details_url = details_link_tag.get("href", None) if details_link_tag else None
            if details_url:
                details_url = "https://www.imoti.net" + details_url

            description_paragraphs = listing.find_all("p")
            try:
                description_paragraphs = description_paragraphs[1].get_text(strip=True)
            except IndexError:
                description_paragraphs = None

            agency = listing.find("span", {"class": self.AGENCY_CLASS, "style": "display:inline-block"})

            if agency:
                agency = agency.get_text(strip=True)
            else:
                agency = None
            title = get_text_or_none(listing, ("h3", {}), strip=False)

            property_type = title.split(",")[0]
            area = title.split(",")[1]
            parameters = listing.find("ul", {"class": "parameters"}).findAll("li")
            if parameters:
                floor = parameters[0].get_text(strip=True)
            else:
                floor = None
            try:
                price_per_m2 = parameters[1].get_text(strip=True)
            except IndexError:
                price_per_m2 = None

            data = {
                "title": title,
                "price_and_currency": get_text_or_none(listing, ("strong", {"class": self.PRICE_CLASS})),
                "location": get_text_or_none(listing, ("span", {"class": self.LOCATION_CLASS})),
                "property_type": property_type,
                "area": area,
                "details_url": details_url,
                "num_photos": get_text_or_none(listing, ("span", {"class": self.PIC_VIDEO_INFO_CLASS})),
                "agency": agency,
                "agency_url": None,  # Agency URL is not present in the listing
                "floor": floor,
                "price_per_m2": price_per_m2,
                "description": description_paragraphs,
                "reference_number": None,
                "is_top_ad": bool(listing.find("span", {"class": self.FLAG_TOP_CLASS})),
                "date_added": datetime.now().isoformat(),
            }
            if not validate_url(data["details_url"]):
                data["details_url"] = None

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

    @classmethod
    def convert_map(cls, property_type: str) -> PropertyType:
        map_property_type = {
            "продава Едностаен апартамент": PropertyType.EDNOSTAEN,
            "продава Двустаен апартамент": PropertyType.DVUSTAEN,
            "продава Тристаен апартамент": PropertyType.TRISTAEN,
            "продава Четиристаен апартамент": PropertyType.CHETIRISTAEN,
        }
        return map_property_type.get(
            property_type,
            "",
        )

    @classmethod
    def to_property_listing_df(cls, df):
        try:
            df["title"] = df["title"]
            df["offer_type"] = df["title"].str.split(" ").str[0].str.strip()

            df["area"] = df["area"]
            df["property_type"] = df["property_type"]
            df["property_type"] = df["property_type"].apply(cls.convert_map)

            df["price"] = (
                df["price_and_currency"]
                .str.extract(r"([\d\s]+)")
                .replace(r"\s+", "", regex=True)
                .astype(int, errors="ignore")
            )
            df["currency"] = df["price_and_currency"].str.extract(r"(EUR|USD|BGN)")[0]

            df["city"] = df["location"].str.split(",").str[0].str.strip()
            df["neighborhood"] = df["location"].str.split(",").str[1].str.strip()

            df["description"] = df["description"]
            df["agency_url"] = df["agency_url"]
            df["agency"] = df["agency"]
            df["details_url"] = df["details_url"]
            df["num_photos"] = df["num_photos"]
            df["date_added"] = df["date_added"]
            df["site"] = Site.IMOTINET
            df["floor"] = df["floor"]
            df["price_per_m2"] = df["price_per_m2"]
            df["ref_no"] = df["reference_number"]

        except Exception as e:
            logger.error(f"Error cleaning imotinet data: {e}", exc_info=True)
        return df
