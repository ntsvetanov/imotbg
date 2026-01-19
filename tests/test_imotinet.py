import pytest
from bs4 import BeautifulSoup

from src.sites.imotinet import ImotiNetParser


SAMPLE_LISTING_HTML = """
<li class="clearfix">
    <a class="box-link" href="/bg/obiavi/prodava/apartament/123"></a>
    <div class="image-container">
        <span class="pic-video-info-number">15</span>
    </div>
    <h3>Двустаен апартамент, 65 кв.м.</h3>
    <span class="location">гр. София, Лозенец</span>
    <p class="summary">Кратко описание</p>
    <p class="description">Пълно описание на имота</p>
    <ul class="parameters">
        <li>5 етаж</li>
        <li>2 500 €/кв.м</li>
    </ul>
    <strong class="price">162 500 €</strong>
    <span class="re-offer-type">Агенция Имоти</span>
</li>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
<ul class="listings">
{SAMPLE_LISTING_HTML}
<li class="clearfix">
    <a class="box-link" href="/bg/obiavi/prodava/apartament/456"></a>
    <h3>Тристаен апартамент, 85 кв.м.</h3>
    <span class="location">гр. Пловдив, Център</span>
    <p>Summary</p>
    <p>Description</p>
    <strong class="price">200 000 лв.</strong>
</li>
</ul>
<nav class="paginator">
    <a href="?page=1">1</a>
    <a href="?page=2">2</a>
    <a class="last-page" href="?page=5">5</a>
</nav>
</body>
</html>
"""


class TestImotiNetParserConfig:
    def test_config_values(self):
        parser = ImotiNetParser()
        assert parser.config.name == "imotinet"
        assert parser.config.base_url == "https://www.imoti.net"
        assert parser.config.encoding == "utf-8"
        assert parser.config.rate_limit_seconds == 1.0


class TestImotiNetParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://imoti.net/search1", "name": "Search 1"},
                {"url": "https://imoti.net/search2", "name": "Search 2"},
            ]
        }
        urls = ImotiNetParser.build_urls(config)
        assert urls == ["https://imoti.net/search1", "https://imoti.net/search2"]

    def test_build_urls_empty(self):
        assert ImotiNetParser.build_urls({}) == []


class TestImotiNetParserExtractListings:
    @pytest.fixture
    def parser(self):
        return ImotiNetParser()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == "162 500 €"

    def test_extract_listing_title(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["title"] == "Двустаен апартамент, 65 кв.м."

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == "гр. София, Лозенец"

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "/bg/obiavi/prodava/apartament/123"

    def test_extract_listing_num_photos(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["num_photos"] == "15"

    def test_extract_listing_agency(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency"] == "Агенция Имоти"

    def test_extract_listing_floor(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["floor"] == "5 етаж"

    def test_extract_listing_price_per_m2(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_per_m2"] == "2 500 €/кв.м"

    def test_extract_listing_area(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["area"] == "65 кв.м."

    def test_extract_listing_description(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["description"] == "Пълно описание на имота"


class TestImotiNetParserTransform:
    @pytest.fixture
    def parser(self):
        return ImotiNetParser()

    def test_transform_listing(self, parser):
        raw = {
            "price_text": "162 500 €",
            "title": "Двустаен апартамент, 65 кв.м.",
            "location": "гр. София, Лозенец",
            "description": "Описание на имота",
            "details_url": "/bg/obiavi/prodava/apartament/123",
            "num_photos": "15",
            "agency": "Агенция Имоти",
            "floor": "5 етаж",
            "price_per_m2": "2 500 €/кв.м",
            "area": "65 кв.м.",
        }
        result = parser.transform_listing(raw)

        assert result.site == "imotinet"
        assert result.price == 162500.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.num_photos == 15
        assert result.details_url == "https://www.imoti.net/bg/obiavi/prodava/apartament/123"
        assert result.area == "65 кв.м."


class TestImotiNetParserPagination:
    @pytest.fixture
    def parser(self):
        return ImotiNetParser()

    def test_get_total_pages(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        assert parser.get_total_pages(soup) == 5

    def test_get_total_pages_no_paginator(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert parser.get_total_pages(soup) == 1

    def test_get_next_page_url(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=abc"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=2&sid=abc"

    def test_get_next_page_url_exceeds_total(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=abc"
        next_url = parser.get_next_page_url(soup, url, 6)

        assert next_url is None


class TestImotiNetParserHelpers:
    @pytest.fixture
    def parser(self):
        return ImotiNetParser()

    def test_extract_area_from_title(self, parser):
        assert parser._extract_area_from_title("Двустаен апартамент, 65 кв.м.") == "65 кв.м."

    def test_extract_area_from_title_no_comma(self, parser):
        assert parser._extract_area_from_title("Апартамент") == ""

    def test_extract_area_from_title_empty(self, parser):
        assert parser._extract_area_from_title("") == ""

    def test_extract_area_from_title_none(self, parser):
        assert parser._extract_area_from_title(None) == ""
