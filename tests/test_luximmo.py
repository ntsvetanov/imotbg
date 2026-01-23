import pytest
from bs4 import BeautifulSoup

from src.sites.luximmo import (
    LuximmoParser,
    extract_city,
    extract_neighborhood,
    extract_area,
    extract_ref_from_url,
)


SAMPLE_LISTING_HTML = """
<div class="card mb-4">
    <a class="card-url" href="https://www.luximmo.bg/za-prodajba/luksozen-imot-43445-tsentyr-sofia.html">Link</a>
    <h4 class="card-title">Тристаен апартамент за продажба</h4>
    <div class="card-price">185 000 €<br/>361 825 лв.</div>
    <div class="card-loc-dis">
        <span class="text-dark">гр. София / кв. Център</span>
    </div>
    <div class="card-dis">Площ: 95.5 м Етаж: 3</div>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
{SAMPLE_LISTING_HTML}
<div class="card mb-4">
    <a class="card-url" href="https://www.luximmo.bg/pod-naem/luksozen-imot-55667-lozenets.html">Link</a>
    <h4 class="card-title">Двустаен апартамент под наем</h4>
    <div class="card-price">800 €/месец</div>
    <div class="card-loc-dis">
        <span class="text-dark">гр. София / кв. Лозенец</span>
    </div>
    <div class="card-dis">Площ: 65 м Етаж: 5</div>
</div>
<ul class="pagination">
    <li><a class="page-link" href="index.html">1</a></li>
    <li><a class="page-link" href="index1.html">2</a></li>
    <li><a class="page-link" href="index2.html">3</a></li>
</ul>
</body>
</html>
"""


class TestExtractCity:
    def test_with_prefix_gr(self):
        assert extract_city("гр. София / кв. Лозенец") == "София"

    def test_with_prefix_grad(self):
        assert extract_city("град София / Център") == "София"

    def test_without_prefix(self):
        assert extract_city("София / Лозенец") == "София"

    def test_empty(self):
        assert extract_city("") == ""

    def test_none(self):
        assert extract_city(None) == ""


class TestExtractNeighborhood:
    def test_with_kv_prefix(self):
        assert extract_neighborhood("гр. София / кв. Лозенец") == "Лозенец"

    def test_without_prefix(self):
        assert extract_neighborhood("София / Център") == "Център"

    def test_no_neighborhood(self):
        assert extract_neighborhood("гр. София") == ""

    def test_empty(self):
        assert extract_neighborhood("") == ""


class TestExtractArea:
    def test_standard_format(self):
        assert extract_area("95.5 м²") == "95.5"

    def test_with_comma(self):
        assert extract_area("207,43 м²") == "207.43"

    def test_integer(self):
        assert extract_area("100 м²") == "100"

    def test_no_match(self):
        assert extract_area("No area here") == ""

    def test_empty(self):
        assert extract_area("") == ""


class TestExtractRefFromUrl:
    def test_standard_ref(self):
        assert extract_ref_from_url("https://luximmo.bg/za-prodajba/luksozen-imot-43445-sofia.html") == "43445"

    def test_no_ref(self):
        assert extract_ref_from_url("https://luximmo.bg/other-page.html") == ""

    def test_empty(self):
        assert extract_ref_from_url("") == ""

    def test_none(self):
        assert extract_ref_from_url(None) == ""


class TestLuximmoParserConfig:
    def test_config_values(self):
        parser = LuximmoParser()
        assert parser.config.name == "luximmo"
        assert parser.config.base_url == "https://www.luximmo.bg"
        assert parser.config.encoding == "utf-8"
        assert parser.config.rate_limit_seconds == 1.5


class TestLuximmoParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://luximmo.bg/sofia/apartments/index.html", "name": "Sofia Apartments"},
                {"url": "https://luximmo.bg/plovdiv/houses/index.html", "name": "Plovdiv Houses"},
            ]
        }
        urls = LuximmoParser.build_urls(config)
        assert urls == [
            {"url": "https://luximmo.bg/sofia/apartments/index.html", "name": "Sofia Apartments"},
            {"url": "https://luximmo.bg/plovdiv/houses/index.html", "name": "Plovdiv Houses"},
        ]

    def test_build_urls_empty(self):
        assert LuximmoParser.build_urls({}) == []


class TestLuximmoParserExtractListings:
    @pytest.fixture
    def parser(self):
        return LuximmoParser()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "185000" in listings[0]["price_text"] or "185 000" in listings[0]["price_text"]

    def test_extract_listing_title(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["title"] == "Тристаен апартамент за продажба"

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "София" in listings[0]["location"]
        assert "Център" in listings[0]["location"]

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "43445" in listings[0]["details_url"]
        assert "za-prodajba" in listings[0]["details_url"]

    def test_extract_listing_area_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "95.5" in listings[0]["area_text"]

    def test_extract_listing_floor(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["floor"] == "3"

    def test_extract_listing_ref_no(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["ref_no"] == "43445"

    def test_extract_listing_offer_type_sell(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["offer_type"] == "продава"

    def test_extract_listing_offer_type_rent(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[1]["offer_type"] == "наем"

    def test_extract_listing_agency_name(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency_name"] == "Luximmo"


class TestLuximmoParserTransform:
    @pytest.fixture
    def parser(self):
        return LuximmoParser()

    def test_transform_listing(self, parser):
        raw = {
            "price_text": "185000 €",
            "title": "Тристаен апартамент за продажба",
            "location": "гр. София / кв. Център",
            "area_text": "95.5 м",
            "floor": "3",
            "description": "",
            "details_url": "https://www.luximmo.bg/za-prodajba/imot-43445.html",
            "ref_no": "43445",
            "offer_type": "продава",
            "agency_name": "Luximmo",
        }
        result = parser.transform_listing(raw)

        assert result.site == "luximmo"
        assert result.price == 185000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"
        assert result.offer_type == "продава"
        assert result.area == "95.5"
        assert result.floor == "3"
        assert result.ref_no == "43445"

    def test_transform_listing_bgn(self, parser):
        raw = {
            "price_text": "250 000 лв.",
            "title": "Двустаен апартамент",
            "location": "гр. Пловдив / кв. Център",
            "area_text": "65 м",
            "floor": "",
            "description": "",
            "details_url": "https://www.luximmo.bg/imot-123.html",
            "ref_no": "123",
            "offer_type": "продава",
            "agency_name": "Luximmo",
        }
        result = parser.transform_listing(raw)

        assert result.price == 250000.0
        assert result.currency == "BGN"

    def test_transform_listing_rent(self, parser):
        raw = {
            "price_text": "800 €",
            "title": "Двустаен апартамент под наем",
            "location": "гр. София / кв. Лозенец",
            "area_text": "65 м",
            "floor": "5",
            "description": "",
            "details_url": "https://www.luximmo.bg/pod-naem/imot-555.html",
            "ref_no": "555",
            "offer_type": "наем",
            "agency_name": "Luximmo",
        }
        result = parser.transform_listing(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"


class TestLuximmoParserPagination:
    @pytest.fixture
    def parser(self):
        return LuximmoParser()

    def test_get_total_pages(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        total = parser.get_total_pages(soup)
        assert total == 3

    def test_get_total_pages_no_pagination(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        total = parser.get_total_pages(soup)
        assert total == 1

    def test_get_next_page_url_page_1(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = parser.get_next_page_url(soup, url, 1)
        assert next_url == "https://www.luximmo.bg/sofia/apartments/index.html"

    def test_get_next_page_url_page_2(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert next_url == "https://www.luximmo.bg/sofia/apartments/index1.html"

    def test_get_next_page_url_page_3(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index1.html"
        next_url = parser.get_next_page_url(soup, url, 3)
        assert next_url == "https://www.luximmo.bg/sofia/apartments/index2.html"

    def test_get_next_page_url_beyond_total(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = parser.get_next_page_url(soup, url, 4)
        assert next_url is None

    def test_get_next_page_url_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert next_url is None

    def test_get_next_page_url_no_index_in_url(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert "index1.html" in next_url


class TestLuximmoParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return LuximmoParser()

    def test_extract_listings_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listings_card_without_url(self, parser):
        html = """
        <div class="card mb-4">
            <h4 class="card-title">No URL Card</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, parser):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <div class="card-price">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["title"] == ""

    def test_extract_listing_missing_price(self, parser):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == ""

    def test_extract_listing_missing_location(self, parser):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-price">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == ""

    def test_extract_listing_missing_area(self, parser):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-dis">Some other info</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["area_text"] == ""

    def test_extract_listing_missing_floor(self, parser):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-dis">Площ: 50 м</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["floor"] == ""

    def test_offer_type_from_title(self, parser):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент под наем</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["offer_type"] == "наем"

    def test_transform_missing_location(self, parser):
        raw = {
            "price_text": "100 €",
            "title": "Test",
            "location": "",
            "area_text": "",
            "floor": "",
            "description": "",
            "details_url": "https://luximmo.bg/imot.html",
            "ref_no": "",
            "offer_type": "",
            "agency_name": "Luximmo",
        }
        result = parser.transform_listing(raw)
        assert result.city == ""
        assert result.neighborhood == ""
