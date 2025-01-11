from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field, ValidationError

from src.logger_setup import get_logger
from src.models import Currency, ListingData, ListingSite, OfferType, PropertyType
from src.utils import get_tag_href_or_none, get_tag_text_or_none, parse_soup

logger = get_logger(__name__)


class RawImotBgListingData(BaseModel):
    listing_id: Optional[str] = Field(None, description="Unique identifier for the listing.")
    price: Optional[str] = Field(None, description="Price of the listing in the appropriate currency.")
    title: Optional[str] = Field(None, description="Title of the listing.")
    location: Optional[str] = Field(None, description="Location details of the listing.")
    description: Optional[str] = Field(None, description="Description of the listing.")
    contact_info: Optional[str] = Field(None, description="Contact information for the listing.")
    agency_url: Optional[str] = Field(None, description="URL of the agency managing the listing.")
    details_url: Optional[str] = Field(None, description="URL with detailed information about the listing.")
    num_photos: Optional[str] = Field(None, description="Number of photos available for the listing.")
    date_added: Optional[datetime] = Field(None, description="Date when the listing was added.")
    offer_type: Optional[str] = Field(None, description="Type of offer (e.g., sale, rent, etc.).")
    search_url: Optional[str] = Field(None, description="URL used to fetch the listing data.")
    total_offers: Optional[int] = Field(None, description="Total number of offers found on the search URL.")

    @classmethod
    def to_property_type(cls, x: str) -> Optional[PropertyType]:
        property_map = {
            "1-СТАЕН": PropertyType.EDNOSTAEN,
            "2-СТАЕН": PropertyType.DVUSTAEN,
            "3-СТАЕН": PropertyType.TRISTAEN,
            "4-СТАЕН": PropertyType.CHETIRISTAEN,
            "МЕЗОНЕТ": PropertyType.MEZONET,
            "МНОГОСТАЕН": PropertyType.MNOGOSTAEN,
            "ЗЕМЕДЕЛСКА ЗЕМЯ": PropertyType.LAND,
        }
        return property_map.get(x, None)

    @classmethod
    def to_offer_type(cls, x: str) -> Optional[OfferType]:
        offer_map = {
            "продава": OfferType.SELL,
            "дава под наем": OfferType.RENT,
        }
        return offer_map.get(x.lower(), None)

    @classmethod
    def to_currency(cls, x: str) -> Optional[Currency]:
        currency_map = {
            "eur": Currency.EUR,
            "bgn": Currency.BGN,
            "лв.": Currency.BGN,
        }
        return currency_map.get(x.lower(), None)

    @classmethod
    def to_price(cls, x: str) -> float:
        if x is None:
            return 0.0
        if not x:
            return 0.0
        if isinstance(x, str):
            x = x.replace(" ", "")
        try:
            return float(x)
        except ValueError:
            return 0.0

    @classmethod
    def to_listing_data(cls, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            logger.warning("Input DataFrame is empty.")
            return pd.DataFrame()

        listing_df = pd.DataFrame()

        # Process columns
        listing_df["raw_title"] = df["title"]
        listing_df["raw_description"] = df["description"]

        # Extract price and currency
        price = df["price"].str.extract(r"(\d{1,3}(?: \d{3})*|\d+)")
        currency = df["price"].str.extract(r"(?i)(eur|bgn|лв.)").fillna("")
        dds = df["price"].str.contains(r"(?:ДДС|без ДДС)", case=False, na=False)

        listing_df["price"] = price[0].apply(cls.to_price)
        listing_df["currency"] = currency[0].apply(cls.to_currency)
        listing_df["without_dds"] = dds

        # Process title for offer type and property type
        process_title = df["title"].str.split()
        listing_df["offer_type"] = process_title.str.get(0).apply(cls.to_offer_type)
        listing_df["property_type"] = process_title.str.get(1).apply(cls.to_property_type)

        # Process location
        processed_location = df["location"].str.split(",")
        listing_df["city"] = (
            processed_location.str.get(0)
            .str.replace(r"\bград\b", "", regex=True)
            .str.replace(r"\bгр. \b", "", regex=True)
            .str.replace(r"\bс. \b", "", regex=True)
            .str.strip()
        )
        listing_df["neighborhood"] = processed_location.str.get(1)

        # Map remaining columns
        listing_df["contact_info"] = df["contact_info"]
        listing_df["agency"] = None
        listing_df["agency_url"] = df["agency_url"]
        listing_df["details_url"] = df["details_url"]
        listing_df["num_photos"] = df["num_photos"]
        listing_df["search_url"] = df["search_url"]
        listing_df["site"] = ListingSite.IMOT_BG
        listing_df["total_offers"] = df["total_offers"]
        listing_df["ref_no"] = df["listing_id"]
        listing_df["date_time_added"] = pd.to_datetime(df["date_added"], errors="coerce")
        listing_df["date"] = listing_df["date_time_added"].dt.date

        validated_rows = []
        for index, row in listing_df.iterrows():
            try:
                validated_row = ListingData(**row.to_dict())
                validated_rows.append(validated_row.model_dump())
            except ValidationError as e:
                logger.error(f"Validation error at row {index}: {e}. Row data: {row.to_dict()}")

        result_df = pd.DataFrame(validated_rows)
        result_df = result_df.fillna("")
        return result_df


class ImotBgParser:
    PRICE_DIV_CLASS = "price"
    TITLE_LINK_CLASS = "lnk1"
    LOCATION_LINK_CLASS = "lnk2"
    DETAILS_LINK_CLASS = "lnk3"
    AGENCY_LOGO_CLASS = "logoLink"
    DESCRIPTION_CELL_PROPS = {"width": "520", "colspan": "3"}
    PAGE_NUMBER_INFO_CLASS = "pageNumbersInfo"
    PHONE_LABEL = "тел.:"
    ADV_QUERY_PARAM = "adv="
    PROTOCOL = "https:"
    DETAILS_TEXT_KEYWORD = "снимки"

    def get_all_listing_tables(self, soup: BeautifulSoup) -> List[Tag]:
        if not soup:
            raise ValueError("Soup object is not initialized.")

        tables = soup.find_all("table")
        listing_tables = [table for table in tables if table.find("div", class_=self.PRICE_DIV_CLASS)]
        logger.info(f"Found {len(listing_tables)} listing tables.")
        return listing_tables

    def extract_listing_data(
        self,
        table: Tag,
        search_url: str,
    ) -> RawImotBgListingData:
        try:
            title_tag = table.find("a", class_=self.TITLE_LINK_CLASS)
            description_td = table.find("td", self.DESCRIPTION_CELL_PROPS)
            details_tag = table.find(
                "a",
                class_=self.DETAILS_LINK_CLASS,
                text=lambda text: text and self.DETAILS_TEXT_KEYWORD in text,
            )
            date_added = datetime.now().isoformat()
            try:
                offer_type = title_tag.get_text(strip=True).split(" ")[0]
            except AttributeError:
                offer_type = None

            result = {
                "price": get_tag_text_or_none(table, ("div", {"class": self.PRICE_DIV_CLASS})),
                "title": title_tag.get_text(strip=True) if title_tag else None,
                "listing_id": (
                    title_tag.get("href", "").split(self.ADV_QUERY_PARAM)[1].split("&")[0]
                    if title_tag and self.ADV_QUERY_PARAM in title_tag.get("href", "")
                    else None
                ),
                "location": get_tag_text_or_none(table, ("a", {"class": self.LOCATION_LINK_CLASS})),
                "description": (description_td.get_text(strip=True) if description_td else None),
                "contact_info": (
                    description_td.get_text(strip=True).split(self.PHONE_LABEL)[-1].strip()
                    if description_td and self.PHONE_LABEL in description_td.get_text(strip=True)
                    else None
                ),
                "agency_url": f"{self.PROTOCOL}{get_tag_href_or_none(table, self.AGENCY_LOGO_CLASS)}",
                "details_url": (f"{self.PROTOCOL}{title_tag.get('href', '')}" if title_tag else None),
                "num_photos": (details_tag.get_text(strip=True).split(" ")[-2] if details_tag else None),
                "date_added": date_added,
                "search_url": search_url,
                "offer_type": offer_type,
            }

            return RawImotBgListingData(**result)
        except ValidationError as ve:
            logger.error(f"Validation error for listing data: {ve}", exc_info=True)
            return RawImotBgListingData()

    def parse_listings(
        self,
        page_content: str,
        search_url: str,
    ) -> List[Dict]:
        try:
            soup = parse_soup(page_content)
            tables = self.get_all_listing_tables(soup)
            return [
                self.extract_listing_data(
                    table=table,
                    search_url=search_url,
                )
                for table in tables
            ]
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
