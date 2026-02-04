"""Extractor for suprimmo.bg real estate listings."""

import re
from datetime import datetime
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing


class SuprimmoExtractor(BaseExtractor):
    """Extractor for suprimmo.bg."""

    config = SiteConfig(
        name="suprimmo",
        base_url="https://www.suprimmo.bg",
        encoding="windows-1251",
        rate_limit_seconds=1.5,
        use_cloudscraper=True,
    )

    def _extract_total_offers(self, soup: BeautifulSoup) -> int:
        elem = soup.select_one("p.font-medium.font-semibold")
        if elem and (match := re.search(r"(\d+)\s*намерени", elem.get_text())):
            return int(match.group(1))
        return 0

    def _detect_offer_type(self, soup: BeautifulSoup) -> str:
        script = soup.select_one("script:-soup-contains('listing_pagetype')")
        if script:
            text = script.get_text().lower()
            if "type:'продава'" in text or "type:'продажба'" in text:
                return "продава"
            if "type:'наем'" in text:
                return "наем"
        return ""

    def _get_details_url(self, card: Tag) -> str:
        link = card.select_one("a.lnk")
        if link and link.get("href"):
            return link["href"]
        btn = card.select_one("div.foot a.button[href*='/imot-']")
        return btn["href"] if btn else ""

    def _get_price(self, card: Tag) -> str:
        elem = card.select_one("div.prc")
        if not elem:
            return ""
        text = elem.get_text(separator=" ", strip=True).replace("\xa0", " ")
        if match := re.search(r"([\d\s]+)\s*€", text):
            return f"{match.group(1).strip()} €"
        return text

    def _get_location(self, card: Tag) -> str:
        elem = card.select_one("div.loc")
        if not elem:
            return ""
        for marker in elem.select("a.property_map"):
            marker.extract()
        return elem.get_text(separator=" / ", strip=True)

    def _get_title(self, card: Tag, offer_type: str) -> str:
        elem = card.select_one("div.ttl")
        if not elem:
            return ""
        for icon in elem.select("i"):
            icon.extract()
        title = elem.get_text(strip=True)
        return self.prepend_offer_type(title, offer_type)

    def _get_detail(self, card: Tag, field: str) -> str:
        elem = card.select_one("div.lst")
        if not elem:
            return ""
        text = elem.get_text(strip=True)
        patterns = {
            "area": r"Площ:\s*([\d.,]+\s*м)",
            "floor": r"Етаж:\s*(\d+)",
            "total_floors": r"Етажност на сградата:\s*(\d+)",
        }
        if match := re.search(patterns[field], text, re.IGNORECASE):
            return match.group(1)
        return ""

    def _get_badges(self, card: Tag) -> str:
        return self.extract_badges(card, "span.badge", exclude_classes=["has_luximo"])

    def _get_raw_link_description(self, card: Tag) -> str:
        link = card.select_one("a.lnk")
        return link.get("title", "") if link else ""

    def extract_listings(self, content: Any) -> Iterator[RawListing]:
        soup: BeautifulSoup = content
        total_offers = self._extract_total_offers(soup)
        offer_type = self._detect_offer_type(soup)
        scraped_at = datetime.now()

        for card in soup.select("div.panel.offer"):
            yield RawListing(
                site=self.config.name,
                scraped_at=scraped_at,
                details_url=self._get_details_url(card),
                price_text=self._get_price(card),
                location_text=self._get_location(card),
                title=self._get_title(card, offer_type),
                description=self._get_badges(card),
                area_text=self._get_detail(card, "area"),
                floor_text=self._get_detail(card, "floor"),
                total_floors_text=self._get_detail(card, "total_floors"),
                agency_name="Suprimmo",
                num_photos=len(card.select("div.slider-embed div.item")),
                ref_no=card.get("data-prop-id", ""),
                total_offers=total_offers,
                raw_link_description=self._get_raw_link_description(card),
            )

    def get_total_pages(self, content: Any) -> int:
        soup: BeautifulSoup = content
        elem = soup.select_one("p.font-medium.font-semibold")
        if elem and (match := re.search(r"от\s*(\d+)", elem.get_text())):
            return int(match.group(1))
        return self.config.max_pages if soup.select_one("link[rel='next']") else 1

    def get_next_page_url(self, content: Any, current_url: str, page_number: int) -> str | None:
        soup: BeautifulSoup = content
        if not soup.select("div.panel.offer"):
            return None

        next_link = soup.select_one("link[rel='next']")
        if not next_link:
            return None

        if page_number == 2:
            return next_link.get("href")

        base_url = re.sub(r"/page/\d+/?$", "", current_url.rstrip("/"))
        return f"{base_url}/page/{page_number}/"
