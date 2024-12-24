from typing import Dict, List

from bs4 import BeautifulSoup

from src.logger_setup import get_logger
from src.utils import get_text_or_none

logger = get_logger(__name__)


class ImotiNetParser:
    def extract_listing_data(self, listing: BeautifulSoup) -> Dict:
        try:
            image_tag = listing.find("img")
            image_url = image_tag.get("src", None) if image_tag else None

            details_link_tag = listing.find("a", {"class": "box-link"})
            details_url = details_link_tag.get("href", None) if details_link_tag else None

            description_paragraphs = listing.find_all("p")
            reference_number = None
            description = None
            for paragraph in description_paragraphs:
                text = paragraph.get_text(strip=True)
                if "Референтен номер:" in text:
                    reference_number = text.split("Референтен номер:")[-1].strip()
                elif not description:
                    description = text

            data = {
                "title": get_text_or_none(listing, ("h3", {})),
                "price": get_text_or_none(listing, ("strong", {"class": "price"})),
                "location": get_text_or_none(listing, ("span", {"class": "location"})),
                "details_url": details_url,
                "images": {
                    "count": get_text_or_none(listing, ("span", {"class": "pic-video-info-number"})),
                    "url": image_url,
                },
                "agency": get_text_or_none(listing, ("span", {"class": "re-offer-type"})),
                "floor": get_text_or_none(listing, ("li", {"text": lambda t: t and "Етаж:" in t})),
                "price_per_m2": get_text_or_none(listing, ("li", {"text": lambda t: t and "Цена на /м" in t})),
                "description": description,
                "reference_number": reference_number,
                "is_top_ad": bool(listing.find("span", {"class": "flag flag-top absolute"})),
            }

            if data["details_url"] and not data["details_url"].startswith("http"):
                data["details_url"] = f"https://www.imoti.net{data['details_url']}"

            if data["images"]["url"] and not data["images"]["url"].startswith("http"):
                data["images"]["url"] = f"https://www.imoti.net{data['images']['url']}"

            return data

        except Exception as e:
            logger.error(f"Error extracting listing data: {e}", exc_info=True)
            return {}

    def parse_listings(self, page_content: str) -> List[Dict]:
        soup = BeautifulSoup(page_content, "html.parser")

        listings = soup.find_all("li", {"class": "clearfix"})
        return [self.extract_listing_data(listing) for listing in listings]

    def get_total_pages(self, page_content: str) -> int:
        soup = BeautifulSoup(page_content, "html.parser")

        paginator = soup.find("nav", {"class": "paginator"})

        try:
            if paginator:
                last_page_link = paginator.find("a", {"class": "last-page"})

                if last_page_link:
                    return int(last_page_link.text.strip())

            return 1

        except Exception as e:
            logger.error(f"Error extracting total pages: {e}", exc_info=True)
            return 1
