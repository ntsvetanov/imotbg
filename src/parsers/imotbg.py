from datetime import datetime
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, HttpUrl, ValidationError

from src.logger_setup import get_logger
from src.utils import get_tag_href_or_none, get_tag_text_or_none, parse_soup

logger = get_logger(__name__)


class ImotBgListingData(BaseModel):
    price: Optional[str]
    title: Optional[str]
    listing_id: Optional[str]
    location: Optional[str]
    description: Optional[str]
    contact_info: Optional[str]
    agency_url: Optional[HttpUrl]
    details_url: Optional[HttpUrl]
    num_photos: Optional[str]
    date_added: Optional[datetime]


class ImotBg:
    PRICE_DIV_CLASS = "price"
    LOCATION_LINK_CLASS = "lnk2"
    TITLE_LINK_CLASS = "lnk1"
    DETAILS_LINK_CLASS = "lnk3"
    AGENCY_LOGO_CLASS = "logoLink"
    DESCRIPTION_CELL_PROPS = {"width": "520", "colspan": "3"}
    PAGE_NUMBER_INFO_CLASS = "pageNumbersInfo"
    PHONE_LABEL = "тел.:"
    ADV_QUERY_PARAM = "adv="
    PROTOCOL = "https:"
    DETAILS_TEXT_KEYWORD = "снимки"

    def __init__(self):
        self.soup = None

    def get_all_listing_tables(self, soup: BeautifulSoup) -> List[Tag]:
        if not soup:
            raise ValueError("Soup object is not initialized.")

        tables = soup.find_all("table")
        listing_tables = [table for table in tables if table.find("div", class_=self.PRICE_DIV_CLASS)]
        logger.info(f"Found {len(listing_tables)} listing tables.")
        return listing_tables

    def extract_listing_data(self, table: Tag) -> ImotBgListingData:
        try:
            title_tag = table.find("a", class_=self.TITLE_LINK_CLASS)
            description_td = table.find("td", self.DESCRIPTION_CELL_PROPS)
            details_tag = table.find(
                "a",
                class_=self.DETAILS_LINK_CLASS,
                text=lambda text: text and self.DETAILS_TEXT_KEYWORD in text,
            )
            date_added = datetime.now().isoformat()
            result = {
                "price": get_tag_text_or_none(table, ("div", {"class": self.PRICE_DIV_CLASS})),
                "title": title_tag.get_text(strip=True) if title_tag else None,
                "listing_id": (
                    title_tag.get("href", "").split(self.ADV_QUERY_PARAM)[1].split("&")[0]
                    if title_tag and self.ADV_QUERY_PARAM in title_tag.get("href", "")
                    else None
                ),
                "location": get_tag_text_or_none(table, ("a", {"class": self.LOCATION_LINK_CLASS})),
                "description": description_td.get_text(strip=True) if description_td else None,
                "contact_info": (
                    description_td.get_text(strip=True).split(self.PHONE_LABEL)[-1].strip()
                    if description_td and self.PHONE_LABEL in description_td.get_text(strip=True)
                    else None
                ),
                "agency_url": f"{self.PROTOCOL}{get_tag_href_or_none(table, self.AGENCY_LOGO_CLASS)}",
                "details_url": f"{self.PROTOCOL}{details_tag.get('href', '')}" if details_tag else None,
                "num_photos": (details_tag.get_text(strip=True).split(" ")[-2] if details_tag else None),
                "date_added": date_added,
            }

            return ImotBgListingData(**result)
        except ValidationError as ve:
            logger.error(f"Validation error for listing data: {ve}")
            return ImotBgListingData()

    def parse_listings(self, page_content: str) -> List[Dict]:
        try:
            soup = parse_soup(page_content)
            tables = self.get_all_listing_tables(soup)
            return [self.extract_listing_data(table) for table in tables]
        except Exception as e:
            logger.error(f"Error parsing listings: {e}", exc_info=True)
            return []

    def get_total_pages(self, page_content: str) -> int:
        try:
            soup = parse_soup(page_content)
            page_info = soup.find("span", class_=self.PAGE_NUMBER_INFO_CLASS)
            if page_info:
                total_pages_text = page_info.get_text(strip=True)
                logger.info(f"Total pages text: {total_pages_text}")
                return int(total_pages_text.split("от")[-1].strip())
            return 1
        except Exception as e:
            logger.error(f"Error fetching total pages: {e}", exc_info=True)
            return 1
