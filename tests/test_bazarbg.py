import pytest
from bs4 import BeautifulSoup

from src.sites.bazarbg import (
    BazarBgParser,
    extract_location_city,
    extract_location_neighborhood,
)

SAMPLE_LISTING_HTML = """
<div class="listItemContainer">
    <a class="listItemLink" href="/ad/12345" title="Продава 2-стаен апартамент" data-id="12345">
        <span class="price">179 000 EUR</span>
        <span class="location">гр. София, Лозенец</span>
        <span class="date">19.01.2026</span>
    </a>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
{SAMPLE_LISTING_HTML}
<div class="listItemContainer">
    <a class="listItemLink" href="/ad/67890" title="Продава 3-стаен апартамент" data-id="67890">
        <span class="price">250 000 лв.</span>
        <span class="location">гр. Пловдив, Център</span>
        <span class="date">18.01.2026</span>
    </a>
</div>
<div class="paging">
    <a class="btn current">1</a>
    <a class="btn not-current" href="?page=2">2</a>
    <a class="btn not-current" href="?page=3">3</a>
    <a class="btn not-current" href="?page=10">10</a>
</div>
</body>
</html>
"""


class TestExtractLocationHelpers:
    def test_extract_location_city(self):
        assert extract_location_city("гр. София, Лозенец") == "София"

    def test_extract_location_city_no_neighborhood(self):
        assert extract_location_city("гр. София") == "София"

    def test_extract_location_city_empty(self):
        assert extract_location_city("") == ""

    def test_extract_location_city_none(self):
        assert extract_location_city(None) == ""

    def test_extract_location_neighborhood(self):
        assert extract_location_neighborhood("гр. София, Лозенец") == "Лозенец"

    def test_extract_location_neighborhood_multiple_parts(self):
        # Neighborhood is normalized - extra address parts are stripped
        assert extract_location_neighborhood("гр. София, Лозенец, ул. Тест") == "Лозенец"

    def test_extract_location_neighborhood_no_comma(self):
        assert extract_location_neighborhood("гр. София") == ""

    def test_extract_location_neighborhood_empty(self):
        assert extract_location_neighborhood("") == ""

    def test_extract_location_neighborhood_none(self):
        assert extract_location_neighborhood(None) == ""


class TestBazarBgParserConfig:
    def test_config_values(self):
        parser = BazarBgParser()
        assert parser.config.name == "bazarbg"
        assert parser.config.base_url == "https://bazar.bg"
        assert parser.config.encoding == "utf-8"
        assert parser.config.rate_limit_seconds == 1.5


class TestBazarBgParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://bazar.bg/search1", "name": "Search 1"},
                {"url": "https://bazar.bg/search2", "name": "Search 2"},
            ]
        }
        urls = BazarBgParser.build_urls(config)
        assert urls == [
            {"url": "https://bazar.bg/search1", "name": "Search 1"},
            {"url": "https://bazar.bg/search2", "name": "Search 2"},
        ]

    def test_build_urls_empty(self):
        assert BazarBgParser.build_urls({}) == []


class TestBazarBgParserExtractListings:
    @pytest.fixture
    def parser(self):
        return BazarBgParser()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_title(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["title"] == "Продава 2-стаен апартамент"

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "/ad/12345"

    def test_extract_listing_ref_no(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["ref_no"] == "12345"

    def test_extract_listing_price_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == "179 000 EUR"

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == "гр. София, Лозенец"

    def test_extract_listing_date(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["date"] == "19.01.2026"

    def test_extract_listing_offer_type_from_title(self, parser, soup):
        """Test offer_type is extracted from title when present."""
        listings = list(parser.extract_listings(soup))
        # Title is "Продава 2-стаен апартамент" which contains "Продава"
        assert listings[0]["offer_type"] == "продава"

    def test_extract_listing_new_fields(self, parser, soup):
        """Test that new fields are present in extracted listings."""
        listings = list(parser.extract_listings(soup))
        assert "area" in listings[0]
        assert "floor" in listings[0]
        assert "num_photos" in listings[0]
        assert "total_offers" in listings[0]
        assert "offer_type" in listings[0]

    def test_extract_listings_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listings_missing_link(self, parser):
        html = """
        <div class="listItemContainer">
            <span class="other">No link here</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_price(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="location">гр. София</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["price_text"] == ""

    def test_extract_listing_missing_location(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["location"] == ""

    def test_extract_listing_missing_date(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["date"] == ""

    def test_extract_listing_missing_data_id(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["ref_no"] == ""


class TestBazarBgParserTransform:
    @pytest.fixture
    def parser(self):
        return BazarBgParser()

    def test_transform_listing_eur(self, parser):
        raw = {
            "title": "Продава 2-стаен апартамент",
            "price_text": "179 000 EUR",
            "location": "гр. София, Лозенец",
            "details_url": "/ad/12345",
            "ref_no": "12345",
            "date": "19.01.2026",
            "offer_type": "продава",  # Set by extract_listings
        }
        result = parser.transform_listing(raw)

        assert result.site == "bazarbg"
        assert result.price == 179000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.details_url == "https://bazar.bg/ad/12345"
        assert result.ref_no == "12345"

    def test_transform_listing_bgn(self, parser):
        raw = {
            "title": "Продава 3-стаен апартамент",
            "price_text": "250 000 лв.",
            "location": "гр. Пловдив, Център",
            "details_url": "/ad/67890",
            "ref_no": "67890",
            "date": "18.01.2026",
        }
        result = parser.transform_listing(raw)

        assert result.site == "bazarbg"
        assert result.price == 250000.0
        assert result.currency == "BGN"
        assert result.city == "Пловдив"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"

    def test_transform_listing_missing_price(self, parser):
        raw = {
            "title": "Продава апартамент",
            "price_text": "",
            "location": "гр. София",
            "details_url": "/ad/123",
            "ref_no": "123",
            "date": "",
        }
        result = parser.transform_listing(raw)

        assert result.price == 0.0
        assert result.currency == ""

    def test_transform_listing_missing_location(self, parser):
        raw = {
            "title": "Продава апартамент",
            "price_text": "100 EUR",
            "location": "",
            "details_url": "/ad/123",
            "ref_no": "123",
            "date": "",
        }
        result = parser.transform_listing(raw)

        assert result.city == ""
        assert result.neighborhood == ""

    def test_transform_listing_naem(self, parser):
        raw = {
            "title": "Под наем 2-стаен",
            "price_text": "1 000 лв.",
            "location": "гр. София, Витоша",
            "details_url": "/ad/999",
            "ref_no": "999",
            "date": "",
            "offer_type": "наем",  # Set by extract_listings
        }
        result = parser.transform_listing(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"


class TestBazarBgParserPagination:
    @pytest.fixture
    def parser(self):
        return BazarBgParser()

    def test_get_total_pages(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        assert parser.get_total_pages(soup) == 10

    def test_get_total_pages_no_pagination(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert parser.get_total_pages(soup) == 1

    def test_get_total_pages_no_page_links(self, parser):
        html = """
        <html><body>
        <div class="paging">
            <a class="btn current">1</a>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert parser.get_total_pages(soup) == 1

    def test_get_total_pages_non_numeric_last_page(self, parser):
        html = """
        <html><body>
        <div class="paging">
            <a class="btn current">1</a>
            <a class="btn not-current">Next</a>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert parser.get_total_pages(soup) == 1

    def test_get_next_page_url_basic(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search?type=apartment"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://bazar.bg/search?type=apartment&page=2"

    def test_get_next_page_url_no_query(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://bazar.bg/search?page=2"

    def test_get_next_page_url_existing_page(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search?type=apartment&page=2"
        next_url = parser.get_next_page_url(soup, url, 3)

        assert next_url == "https://bazar.bg/search?type=apartment&page=3"

    def test_get_next_page_url_exceeds_total(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search?type=apartment"
        next_url = parser.get_next_page_url(soup, url, 11)

        assert next_url is None

    def test_get_next_page_url_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://bazar.bg/search"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url is None

    def test_get_next_page_url_page_equals_total(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search"
        next_url = parser.get_next_page_url(soup, url, 10)

        assert next_url == "https://bazar.bg/search?page=10"

    def test_get_next_page_url_page_one(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search"
        next_url = parser.get_next_page_url(soup, url, 1)

        assert next_url == "https://bazar.bg/search?page=1"


class TestBazarBgParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return BazarBgParser()

    def test_extract_listing_special_characters_in_title(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="&quot;Луксозен&quot; апартамент &amp; СПА" data-id="123">
                <span class="price">500 000 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert '"Луксозен" апартамент & СПА' in listings[0]["title"]

    def test_extract_listing_whitespace_in_price(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="price">  179 000   EUR  </span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == "179 000   EUR"

    def test_extract_listing_empty_href(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="" title="Test" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["details_url"] == ""

    def test_extract_listing_missing_title_attribute(self, parser):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["title"] == ""

    def test_transform_listing_village_location(self, parser):
        raw = {
            "title": "Продава къща",
            "price_text": "50 000 EUR",
            "location": "с. Равда",
            "details_url": "/ad/123",
            "ref_no": "123",
            "date": "",
        }
        result = parser.transform_listing(raw)

        assert result.city == "Равда"
        assert result.neighborhood == ""

    def test_transform_listing_garage_property_type(self, parser):
        raw = {
            "title": "Продава гараж",
            "price_text": "10 000 EUR",
            "location": "гр. София",
            "details_url": "/ad/123",
            "ref_no": "123",
            "date": "",
            "offer_type": "продава",  # Set by extract_listings
        }
        result = parser.transform_listing(raw)

        # Garage is now a recognized property type
        assert result.property_type == "гараж"
        assert result.offer_type == "продава"

    def test_transform_listing_complex_location(self, parser):
        raw = {
            "title": "Продава 2-стаен",
            "price_text": "100 000 EUR",
            "location": "гр. София, Витоша, ж.к. Манастирски ливади",
            "details_url": "/ad/123",
            "ref_no": "123",
            "date": "",
        }
        result = parser.transform_listing(raw)

        assert result.city == "София"
        # Neighborhood is normalized - first matching neighborhood is used
        assert result.neighborhood in ["Витоша", "Манастирски ливади"]
