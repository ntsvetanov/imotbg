import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.imotinet import ImotiNetExtractor

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
<span id="number-of-estates">/50 имота/</span>
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


class TestImotiNetExtractorConfig:
    def test_config_values(self):
        extractor = ImotiNetExtractor()
        assert extractor.config.name == "imotinet"
        assert extractor.config.base_url == "https://www.imoti.net"
        assert extractor.config.encoding == "utf-8"
        assert extractor.config.rate_limit_seconds == 1.0


class TestImotiNetExtractorBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://imoti.net/search1", "name": "Search 1"},
                {"url": "https://imoti.net/search2", "name": "Search 2"},
            ]
        }
        urls = ImotiNetExtractor.build_urls(config)
        assert urls == [
            {"url": "https://imoti.net/search1", "name": "Search 1"},
            {"url": "https://imoti.net/search2", "name": "Search 2"},
        ]

    def test_build_urls_empty(self):
        assert ImotiNetExtractor.build_urls({}) == []


class TestImotiNetExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return ImotiNetExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == "162 500 €"

    def test_extract_listing_title(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].title == "Двустаен апартамент, 65 кв.м."

    def test_extract_listing_location(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == "гр. София, Лозенец"

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].details_url == "https://www.imoti.net/bg/obiavi/prodava/apartament/123"

    def test_extract_listing_num_photos(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 15

    def test_extract_listing_agency(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == "Агенция Имоти"

    def test_extract_listing_ref_no(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].ref_no == "123"
        assert listings[1].ref_no == "456"

    def test_extract_listing_total_offers(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_offers == 50
        assert listings[1].total_offers == 50

    def test_extract_listing_floor(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == "5 етаж"

    def test_extract_listing_area(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].area_text == "65 кв.м."

    def test_extract_listing_description(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].description == "Пълно описание на имота"


class TestImotiNetTransform:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing(self, transformer):
        raw = RawListing(
            site="imotinet",
            price_text="162 500 €",
            title="Двустаен апартамент, 65 кв.м.",
            location_text="гр. София, Лозенец",
            description="Описание на имота",
            details_url="https://www.imoti.net/bg/obiavi/prodava/apartament/123",
            num_photos=15,
            agency_name="Агенция Имоти",
            floor_text="5 етаж",
            area_text="65 кв.м.",
        )
        result = transformer.transform(raw)

        assert result.site == "imotinet"
        assert result.price == 162500.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.num_photos == 15
        assert result.details_url == "https://www.imoti.net/bg/obiavi/prodava/apartament/123"
        assert result.area == 65.0


class TestImotiNetExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return ImotiNetExtractor()

    def test_get_total_pages(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        assert extractor.get_total_pages(soup) == 5

    def test_get_total_pages_no_paginator(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert extractor.get_total_pages(soup) == 1

    def test_get_next_page_url(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=abc"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=2&sid=abc"

    def test_get_next_page_url_exceeds_total(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1&sid=abc"
        next_url = extractor.get_next_page_url(soup, url, 6)

        assert next_url is None


class TestImotiNetExtractorHelpers:
    @pytest.fixture
    def extractor(self):
        return ImotiNetExtractor()

    def test_extract_area_from_title(self, extractor):
        assert extractor._extract_area_from_title("Двустаен апартамент, 65 кв.м.") == "65 кв.м."

    def test_extract_area_from_title_no_comma(self, extractor):
        assert extractor._extract_area_from_title("Апартамент") == ""

    def test_extract_area_from_title_empty(self, extractor):
        assert extractor._extract_area_from_title("") == ""

    def test_extract_area_from_title_none(self, extractor):
        assert extractor._extract_area_from_title(None) == ""


class TestImotiNetExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return ImotiNetExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_listings_empty(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <li class="clearfix">
            <a class="box-link" href="/bg/obiavi/123"></a>
            <h3>Test Title</h3>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == ""

    def test_extract_listing_missing_location(self, extractor):
        html = """
        <li class="clearfix">
            <a class="box-link" href="/bg/obiavi/123"></a>
            <h3>Test Title</h3>
            <strong class="price">100 EUR</strong>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == ""

    def test_extract_listing_missing_num_photos(self, extractor):
        html = """
        <li class="clearfix">
            <a class="box-link" href="/bg/obiavi/123"></a>
            <h3>Test Title</h3>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos is None

    def test_extract_listing_missing_agency(self, extractor):
        html = """
        <li class="clearfix">
            <a class="box-link" href="/bg/obiavi/123"></a>
            <h3>Test Title</h3>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == ""

    def test_extract_listing_empty_params(self, extractor):
        html = """
        <li class="clearfix">
            <a class="box-link" href="/bg/obiavi/123"></a>
            <h3>Test Title</h3>
            <ul class="parameters"></ul>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == ""

    def test_extract_listing_one_param(self, extractor):
        html = """
        <li class="clearfix">
            <a class="box-link" href="/bg/obiavi/123"></a>
            <h3>Test Title</h3>
            <ul class="parameters">
                <li>3 етаж</li>
            </ul>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == "3 етаж"

    def test_extract_description_no_paragraphs(self, extractor):
        html = """<li class="clearfix"></li>"""
        soup = BeautifulSoup(html, "html.parser")
        listing = soup.select_one("li.clearfix")
        assert extractor._extract_description(listing) == ""

    def test_extract_description_one_paragraph(self, extractor):
        html = """<li class="clearfix"><p>Summary only</p></li>"""
        soup = BeautifulSoup(html, "html.parser")
        listing = soup.select_one("li.clearfix")
        assert extractor._extract_description(listing) == ""

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="imotinet",
            price_text="200 000 лв.",
            title="Тристаен апартамент, 85 кв.м.",
            location_text="гр. Пловдив, Център",
            description="",
            details_url="/bg/obiavi/456",
            num_photos=None,
            agency_name="",
            floor_text="",
            area_text="85 кв.м.",
        )
        result = transformer.transform(raw)

        assert result.price == round(200000.0 / 1.9558, 2)
        assert result.original_currency == "BGN"
        assert result.property_type == "тристаен"

    def test_transform_listing_rent(self, transformer):
        raw = RawListing(
            site="imotinet",
            price_text="500 EUR",
            title="Под наем двустаен, 50 кв.м.",
            location_text="гр. София, Център",
            description="",
            details_url="/bg/obiavi/123",
            num_photos=5,
            agency_name="",
            floor_text="",
            area_text="50 кв.м.",
        )
        result = transformer.transform(raw)

        assert result.offer_type == "наем"
        assert result.num_photos == 5

    def test_transform_listing_missing_num_photos(self, transformer):
        raw = RawListing(
            site="imotinet",
            price_text="100 EUR",
            title="Test",
            location_text="",
            description="",
            details_url="/bg/obiavi/123",
            num_photos=None,
            agency_name="",
            floor_text="",
            area_text="",
        )
        result = transformer.transform(raw)
        assert result.num_photos is None

    def test_get_total_pages_missing_last_page(self, extractor):
        html = """
        <html><body>
        <nav class="paginator">
            <a href="?page=1">1</a>
            <a href="?page=2">2</a>
        </nav>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert extractor.get_total_pages(soup) == 1

    def test_get_next_page_url_page_one(self, extractor):
        html = """
        <html><body>
        <nav class="paginator">
            <a class="last-page" href="?page=3">3</a>
        </nav>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        url = "https://www.imoti.net/search?page=1&other=param"
        next_url = extractor.get_next_page_url(soup, url, 1)
        assert "page=1" in next_url

    def test_get_next_page_url_page_equals_total(self, extractor):
        html = """
        <html><body>
        <nav class="paginator">
            <a class="last-page" href="?page=3">3</a>
        </nav>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        url = "https://www.imoti.net/search?page=1"
        next_url = extractor.get_next_page_url(soup, url, 3)
        assert "page=3" in next_url

    def test_extract_params(self, extractor):
        html = """
        <li class="clearfix">
            <ul class="parameters">
                <li>10 етаж</li>
                <li>3 000 EUR/кв.м</li>
            </ul>
        </li>
        """
        soup = BeautifulSoup(html, "html.parser")
        listing = soup.select_one("li.clearfix")
        floor, price_per_m2 = extractor._extract_params(listing)
        assert floor == "10 етаж"
        assert price_per_m2 == "3 000 EUR/кв.м"

    def test_extract_area_from_title_complex(self, extractor):
        assert extractor._extract_area_from_title("Апартамент, 120 кв.м., луксозен") == "120 кв.м."

    def test_extract_ref_no_from_url(self, extractor):
        assert extractor._extract_ref_no("/bg/obiava/prodava/sofia/oborishte/garaj/6196041/") == "6196041"
        assert extractor._extract_ref_no("/bg/obiavi/prodava/apartament/123") == "123"
        assert extractor._extract_ref_no("/bg/obiavi/prodava/apartament/456?sid=abc") == "456"
        assert extractor._extract_ref_no("") == ""
        assert extractor._extract_ref_no("/bg/obiavi/no-number/") == ""

    def test_extract_total_offers(self, extractor):
        html = '<html><body><span id="number-of-estates">/123 имота/</span></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        assert extractor._extract_total_offers(soup) == 123

    def test_extract_total_offers_999_plus(self, extractor):
        html = '<html><body><span id="number-of-estates">/999+ имота/</span></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        assert extractor._extract_total_offers(soup) == 999

    def test_extract_total_offers_missing(self, extractor):
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extractor._extract_total_offers(soup) == 0
