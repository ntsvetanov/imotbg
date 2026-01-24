import pytest
from bs4 import BeautifulSoup

from src.sites.bulgarianproperties import (
    BulgarianPropertiesParser,
    extract_area,
    extract_city,
    extract_neighborhood,
    extract_ref_no,
)

SAMPLE_LISTING_HTML = """
<div class="component-property-item">
    <a class="title" href="/imoti/apartament-sofia-lozenets/12345.html">Тристаен апартамент в София</a>
    <span class="regular-price">185 000 €</span>
    <span class="location">гр. София, Лозенец</span>
    <span class="size">85 кв.м.</span>
    <div class="list-description">Просторен тристаен апартамент с гледка</div>
    <div class="ref-no">Ref: BP12345</div>
    <div class="broker">
        <div class="broker-info">
            <span class="name">Иван Иванов</span>
        </div>
    </div>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
{SAMPLE_LISTING_HTML}
<div class="component-property-item">
    <a class="title" href="/imoti/apartament-plovdiv/67890.html">Двустаен апартамент под наем</a>
    <span class="new-price">500 €/месец</span>
    <span class="location">гр. Пловдив, Център</span>
    <span class="size">65 m2</span>
</div>
<div class="pagination">
    <a href="?page=1">1</a>
    <a href="?page=2">2</a>
    <a href="?page=3">3</a>
</div>
</body>
</html>
"""


class TestExtractCity:
    def test_with_prefix_gr(self):
        assert extract_city("гр. София, Лозенец") == "София"

    def test_with_prefix_grad(self):
        assert extract_city("град София, Център") == "София"

    def test_with_prefix_s(self):
        assert extract_city("с. Панчарево, София") == "Панчарево"

    def test_without_prefix(self):
        assert extract_city("София, Лозенец") == "София"

    def test_empty(self):
        assert extract_city("") == ""

    def test_none(self):
        assert extract_city(None) == ""


class TestExtractNeighborhood:
    def test_standard(self):
        assert extract_neighborhood("гр. София, Лозенец") == "Лозенец"

    def test_no_neighborhood(self):
        assert extract_neighborhood("гр. София") == ""

    def test_empty(self):
        assert extract_neighborhood("") == ""


class TestExtractArea:
    def test_kv_m_format(self):
        assert extract_area("85 кв.м.") == "85"

    def test_m2_format(self):
        assert extract_area("65 m2") == "65"

    def test_kvm_format(self):
        assert extract_area("100 кв.м") == "100"

    def test_with_decimal_comma(self):
        assert extract_area("95,5 кв.м.") == "95.5"

    def test_with_decimal_dot(self):
        assert extract_area("95.5 кв.м.") == "95.5"

    def test_no_match(self):
        assert extract_area("No area here") == ""

    def test_empty(self):
        assert extract_area("") == ""


class TestExtractRefNo:
    def test_ref_format(self):
        assert extract_ref_no("Ref: BP12345") == "BP12345"

    def test_no_format(self):
        assert extract_ref_no("No. 12345") == "12345"

    def test_number_format(self):
        assert extract_ref_no("№ ABC123") == "ABC123"

    def test_no_match(self):
        assert extract_ref_no("Some other text") == ""

    def test_empty(self):
        assert extract_ref_no("") == ""


class TestBulgarianPropertiesParserConfig:
    def test_config_values(self):
        parser = BulgarianPropertiesParser()
        assert parser.config.name == "bulgarianproperties"
        assert parser.config.base_url == "https://www.bulgarianproperties.bg"
        assert parser.config.encoding == "windows-1251"
        assert parser.config.rate_limit_seconds == 1.5


class TestBulgarianPropertiesParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://bulgarianproperties.bg/sofia/apartments", "name": "Sofia Apartments"},
                {"url": "https://bulgarianproperties.bg/plovdiv/houses", "name": "Plovdiv Houses"},
            ]
        }
        urls = BulgarianPropertiesParser.build_urls(config)
        assert urls == [
            {"url": "https://bulgarianproperties.bg/sofia/apartments", "name": "Sofia Apartments"},
            {"url": "https://bulgarianproperties.bg/plovdiv/houses", "name": "Plovdiv Houses"},
        ]

    def test_build_urls_empty(self):
        assert BulgarianPropertiesParser.build_urls({}) == []


class TestBulgarianPropertiesParserExtractListings:
    @pytest.fixture
    def parser(self):
        return BulgarianPropertiesParser()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "185 000 €" in listings[0]["price_text"]

    def test_extract_listing_title(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["title"] == "Тристаен апартамент в София"

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == "гр. София, Лозенец"

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "/imoti/apartament-sofia-lozenets/12345.html"

    def test_extract_listing_size_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["size_text"] == "85 кв.м."

    def test_extract_listing_description(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "Просторен" in listings[0]["description"]

    def test_extract_listing_ref_no_from_element(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "BP12345" in listings[0]["ref_no"]

    def test_extract_listing_ref_no_from_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        # Second listing has no ref element, should extract from URL
        assert listings[1]["ref_no"] == "67890"

    def test_extract_listing_agency_name(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency_name"] == "Иван Иванов"

    def test_extract_listing_agency_name_default(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        # Second listing has no broker, should use default
        assert listings[1]["agency_name"] == "Bulgarian Properties"

    def test_extract_listing_new_price(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "500" in listings[1]["price_text"]


class TestBulgarianPropertiesParserTransform:
    @pytest.fixture
    def parser(self):
        return BulgarianPropertiesParser()

    def test_transform_listing(self, parser):
        raw = {
            "price_text": "185 000 €",
            "title": "Тристаен апартамент в София",
            "location": "гр. София, Лозенец",
            "size_text": "85 кв.м.",
            "description": "Nice apartment",
            "details_url": "/imoti/apartament/12345.html",
            "ref_no": "BP12345",
            "agency_name": "Agent Name",
        }
        result = parser.transform_listing(raw)

        assert result.site == "bulgarianproperties"
        assert result.price == 185000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "тристаен"
        assert result.area == "85"
        assert result.ref_no == "BP12345"
        # details_url should be prepended with base_url
        assert result.details_url == "https://www.bulgarianproperties.bg/imoti/apartament/12345.html"

    def test_transform_listing_bgn(self, parser):
        raw = {
            "price_text": "250 000 лв.",
            "title": "Двустаен апартамент",
            "location": "гр. Пловдив, Център",
            "size_text": "65 m2",
            "description": "",
            "details_url": "/imoti/123.html",
            "ref_no": "123",
            "agency_name": "Bulgarian Properties",
        }
        result = parser.transform_listing(raw)

        assert result.price == 250000.0
        assert result.currency == "BGN"

    def test_transform_listing_rent(self, parser):
        raw = {
            "price_text": "500 €",
            "title": "Двустаен апартамент под наем",
            "location": "гр. София, Център",
            "size_text": "65 кв.м.",
            "description": "",
            "details_url": "/imoti/555.html",
            "ref_no": "555",
            "agency_name": "Bulgarian Properties",
        }
        result = parser.transform_listing(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"


class TestBulgarianPropertiesParserPagination:
    @pytest.fixture
    def parser(self):
        return BulgarianPropertiesParser()

    def test_get_total_pages(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        total = parser.get_total_pages(soup)
        assert total == 3

    def test_get_total_pages_no_pagination(self, parser):
        html = """
        <html><body>
        <div class="component-property-item">
            <a class="title" href="/imot.html">Test</a>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = parser.get_total_pages(soup)
        # Returns max_pages when no pagination found
        assert total == parser.config.max_pages

    def test_get_next_page_url_page_2(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert next_url == "https://www.bulgarianproperties.bg/sofia/apartments?page=2"

    def test_get_next_page_url_existing_query(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments?type=flat"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert next_url == "https://www.bulgarianproperties.bg/sofia/apartments?type=flat&page=2"

    def test_get_next_page_url_replace_page(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments?page=2"
        next_url = parser.get_next_page_url(soup, url, 3)
        assert next_url == "https://www.bulgarianproperties.bg/sofia/apartments?page=3"

    def test_get_next_page_url_beyond_total(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments"
        next_url = parser.get_next_page_url(soup, url, 4)
        assert next_url is None

    def test_get_next_page_url_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert next_url is None


class TestBulgarianPropertiesParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return BulgarianPropertiesParser()

    def test_extract_listings_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, parser):
        html = """
        <div class="component-property-item">
            <span class="regular-price">100 €</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["title"] == ""

    def test_extract_listing_missing_price(self, parser):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == ""

    def test_extract_listing_missing_location(self, parser):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
            <span class="regular-price">100 €</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == ""

    def test_extract_listing_missing_size(self, parser):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["size_text"] == ""

    def test_extract_listing_missing_description(self, parser):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["description"] == ""

    def test_extract_listing_alternative_link_selector(self, parser):
        html = """
        <div class="component-property-item">
            <div class="property-item-top">
                <a class="image" href="/imoti/alt-123.html">Image</a>
            </div>
            <div class="content">
                <div class="title">Апартамент</div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "/imoti/alt-123.html"

    def test_transform_missing_location(self, parser):
        raw = {
            "price_text": "100 €",
            "title": "Test",
            "location": "",
            "size_text": "",
            "description": "",
            "details_url": "/imot.html",
            "ref_no": "",
            "agency_name": "Bulgarian Properties",
        }
        result = parser.transform_listing(raw)
        assert result.city == ""
        assert result.neighborhood == ""

    def test_details_url_prepend(self, parser):
        raw = {
            "price_text": "100 €",
            "title": "Test",
            "location": "",
            "size_text": "",
            "description": "",
            "details_url": "/relative/path.html",
            "ref_no": "",
            "agency_name": "Bulgarian Properties",
        }
        result = parser.transform_listing(raw)
        assert result.details_url == "https://www.bulgarianproperties.bg/relative/path.html"

    def test_details_url_already_absolute(self, parser):
        raw = {
            "price_text": "100 €",
            "title": "Test",
            "location": "",
            "size_text": "",
            "description": "",
            "details_url": "https://www.bulgarianproperties.bg/absolute/path.html",
            "ref_no": "",
            "agency_name": "Bulgarian Properties",
        }
        result = parser.transform_listing(raw)
        # Should not double-prepend
        assert result.details_url == "https://www.bulgarianproperties.bg/absolute/path.html"
