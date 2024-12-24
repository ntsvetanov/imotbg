from typing import Dict, List

from bs4 import BeautifulSoup

from src.logger_setup import get_logger
from src.utils import get_text_or_none

logger = get_logger(__name__)


class ImotBg:
    PRICE_DIV_CLASS = "price"
    LOCATION_LINK_CLASS = "lnk2"
    TITLE_LINK_CLASS = "lnk1"
    DETAILS_LINK_CLASS = "lnk3"
    AGENCY_LOGO_CLASS = "logoLink"
    DESCRIPTION_CELL_PROPS = {"width": "520", "colspan": "3"}

    def get_all_listing_tables(self, soup: BeautifulSoup) -> List[BeautifulSoup]:
        if not soup:
            raise ValueError("Soup object not initialized.")
        return [table for table in soup.find_all("table") if table.find("div", class_=self.PRICE_DIV_CLASS)]

    def extract_listing_data(self, table: BeautifulSoup) -> Dict:
        data = {
            "price": get_text_or_none(table, ("div", {"class": self.PRICE_DIV_CLASS})),
            "title": None,
            "listing_id": None,
            "location": get_text_or_none(table, ("a", {"class": self.LOCATION_LINK_CLASS})),
            "description": None,
            "contact_info": None,
            "agency_url": None,
            "details_url": None,
            "num_photos": None,
        }

        title_tag = table.find("a", class_=self.TITLE_LINK_CLASS)
        if title_tag:
            href = title_tag.get("href", "")
            data.update(
                {
                    "title": title_tag.get_text(strip=True),
                    "listing_id": href.split("adv=")[1].split("&")[0] if "adv=" in href else None,
                }
            )

        description_td = table.find("td", self.DESCRIPTION_CELL_PROPS)
        if description_td:
            description_text = description_td.get_text(strip=True)
            data.update(
                {
                    "description": description_text,
                    "contact_info": (
                        description_text.split("тел.:")[-1].strip() if "тел.:" in description_text else None
                    ),
                }
            )

        agency_logo_tag = table.find("a", class_=self.AGENCY_LOGO_CLASS)
        if agency_logo_tag:
            data["agency_url"] = f"https:{agency_logo_tag.get('href', '')}"

        details_tag = table.find("a", class_=self.DETAILS_LINK_CLASS, text=lambda text: text and "снимки" in text)
        if details_tag:
            data.update(
                {
                    "details_url": f"https:{details_tag.get('href', '')}",
                    "num_photos": details_tag.get_text(strip=True).split(" ")[-2],
                }
            )

        return data

    def parse_listings(self, page_content: str) -> List[Dict]:
        soup = BeautifulSoup(page_content, "html.parser")
        try:
            tables = self.get_all_listing_tables(soup)
            return [self.extract_listing_data(table) for table in tables]
        except Exception as e:
            logger.error(f"Error parsing listings: {e}")
            return []

    def get_total_pages(self, page_content: str) -> int:
        soup = BeautifulSoup(page_content, "html.parser")
        try:
            page_info = soup.find("span", class_="pageNumbersInfo")
            if page_info:
                total_pages_text = page_info.get_text(strip=True)
                return int(total_pages_text.split("от")[-1].strip())
            return 1
        except Exception as e:
            logger.error(f"Error fetching total pages: {e}")
            return 1
