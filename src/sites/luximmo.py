"""Extractor for luximmo.bg real estate listings."""

import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class LuximmoExtractor(BaseExtractor):
    """Extractor for luximmo.bg."""

    config = SiteConfig(
        name="luximmo",
        base_url="https://www.luximmo.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.5,
        use_cloudscraper=True,
    )

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        """Extract total offers count from page.

        The total is shown in format: "1102 оферти / Страницa 1 от 46"
        """
        elem = soup.select_one("div.found-properties")
        if elem and (match := re.search(r"(\d+)\s*оферт", elem.get_text())):
            return int(match.group(1))
        return 0

    def _detect_offer_type(self, title: str, url: str) -> str:
        combined = f"{title} {url}".lower()
        if "продава" in combined or "prodava" in combined or "prodazhba" in combined:
            return "продава"
        if "наем" in combined or "naem" in combined:
            return "наем"
        return ""

    def _get_price(self, card: Tag) -> str:
        elem = card.select_one(".card-price")
        if not elem:
            return ""
        text = elem.get_text(strip=True).replace("\xa0", " ")
        if match := re.search(r"([\d\s]+)\s*€", text):
            return f"{match.group(1).replace(' ', '')} €"
        return text

    def _get_location(self, card: Tag) -> str:
        elem = card.select_one(".card-loc-dis .text-dark")
        if not elem:
            return ""
        text = elem.get_text(separator=" ", strip=True)
        return re.sub(r"\s*карта\s*$", "", text).strip()

    def _get_detail(self, card: Tag, field: str) -> str:
        elem = card.select_one(".card-dis")
        if not elem:
            return ""
        text = elem.get_text()
        patterns = {
            "area": r"Площ:\s*([\d.,]+\s*м)",
            "floor": r"Етаж:\s*(\d+)",
            "total_floors": r"Етажност:\s*(\d+)",
        }
        if match := re.search(patterns[field], text):
            return match.group(1)
        return ""

    def _get_badges(self, card: Tag) -> str:
        return self.extract_badges(card, ".badge-rights, .card-badge")

    def _get_num_photos(self, card: Tag) -> int:
        counter = card.select_one(".counter-wrapper-card .lastNum")
        if counter and counter.get_text(strip=True).isdigit():
            return int(counter.get_text(strip=True))
        slides = card.select("div.slick-slide")
        if slides:
            return len(slides)
        return len(card.select("div.carousel-item, div.card-img"))

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        soup: BeautifulSoup = content
        total_offers = self._extract_total_offers(soup)
        scraped_at = datetime.now()

        for card in soup.select("div.card.mb-4"):
            url_elem = card.select_one("a.card-url")
            if not url_elem:
                continue

            details_url = url_elem.get("href", "")
            title_elem = card.select_one("h4.card-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            offer_type = self._detect_offer_type(title, details_url)
            title = self.prepend_offer_type(title, offer_type)

            first_img = card.select_one("div.card-img")
            ref_match = re.search(r"imot-(\d+)", details_url)

            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=details_url,
                price_text=self._get_price(card),
                location_text=self._get_location(card),
                title=title,
                description=self._get_badges(card),
                area_text=self._get_detail(card, "area"),
                floor_text=self._get_detail(card, "floor"),
                total_floors_text=self._get_detail(card, "total_floors"),
                agency_name="Luximmo",
                num_photos=self._get_num_photos(card),
                ref_no=ref_match.group(1) if ref_match else "",
                total_offers=total_offers,
                raw_link_description=first_img.get("title", "") if first_img else "",
            )

    def get_total_pages(self, content: Any) -> int:
        soup: BeautifulSoup = content
        pagination = soup.select_one("ul.pagination")
        if not pagination:
            return 1

        max_page = 1
        for link in pagination.select("a.page-link"):
            href = link.get("href", "")
            if match := re.search(r"index(\d+)\.html", href):
                max_page = max(max_page, int(match.group(1)) + 1)
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        soup: BeautifulSoup = content
        if not soup.select("div.card.mb-4 a.card-url"):
            return None

        if page_number > self.get_total_pages(soup):
            return None

        page_index = page_number - 1

        if "index.html" in current_url:
            if page_index == 0:
                return current_url
            return current_url.replace("index.html", f"index{page_index}.html")

        if re.search(r"index\d+\.html", current_url):
            if page_index == 0:
                return re.sub(r"index\d+\.html", "index.html", current_url)
            return re.sub(r"index\d+\.html", f"index{page_index}.html", current_url)

        base = current_url.rstrip("/")
        if page_index > 0:
            return f"{base}/index{page_index}.html"
        return f"{base}/index.html"
