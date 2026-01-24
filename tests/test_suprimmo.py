import pytest
from bs4 import BeautifulSoup

from src.sites.suprimmo import (
    SuprimmoParser,
    calculate_price_per_m2,
    extract_area,
    extract_city,
    extract_floor,
    extract_neighborhood,
    extract_offer_type_from_url,
    extract_ref_from_contact_url,
)

SAMPLE_LISTING_HTML = """
<div class="panel rel shadow offer" data-prop-id="123456">
    <div class="slider-embed">
        <div class="item"><img src="photo1.jpg"/></div>
        <div class="item"><img src="photo2.jpg"/></div>
        <div class="item"><img src="photo3.jpg"/></div>
    </div>
    <a class="lnk" href="/prodajba-imot-apartament-sofia-lozenets-123456.html">Link</a>
    <div class="ttl">Тристаен апартамент</div>
    <div class="prc">185 000 €<br/>361 825 лв.</div>
    <div class="loc">
        <a class="property_map" href="#">Map</a>
        гр. София / кв. Лозенец
    </div>
    <div class="lst">Площ: 95.5 м² Етаж: 3</div>
    <a class="offer-agent-form" href="/agent-contact?ref_no=SOF 109946">Contact</a>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<head>
    <link rel="next" href="https://www.suprimmo.bg/sofia/apartments/page/2/"/>
</head>
<body>
<p class="font-medium font-semibold">1448 намерени оферти / Страницa 1 от 61</p>
<script>
    dataLayer = [{{listing_pagetype: "type:'продава'"}}];
</script>
{SAMPLE_LISTING_HTML}
<div class="panel rel shadow offer" data-prop-id="789012">
    <div class="slider-embed">
        <div class="item"><img src="photo1.jpg"/></div>
    </div>
    <a class="lnk" href="/pod-naem-imot-apartament-sofia-centar-789012.html">Link</a>
    <div class="ttl">Двустаен апартамент</div>
    <div class="prc">500 €/месец</div>
    <div class="loc">гр. София / кв. Център</div>
    <div class="lst">Площ: 65 м² Етаж: партер</div>
</div>
</body>
</html>
"""


class TestExtractCity:
    def test_with_prefix_gr(self):
        assert extract_city("гр. София / кв. Лозенец") == "София"

    def test_with_prefix_s(self):
        assert extract_city("с. Панчарево") == "Панчарево"

    def test_without_prefix(self):
        assert extract_city("София / Лозенец") == "София"

    def test_with_nbsp(self):
        assert extract_city("гр.\xa0София / кв. Лозенец") == "София"

    def test_empty(self):
        assert extract_city("") == ""

    def test_none(self):
        assert extract_city(None) == ""


class TestExtractNeighborhood:
    def test_with_kv_prefix(self):
        assert extract_neighborhood("гр. София / кв. Лозенец") == "Лозенец"

    def test_without_prefix(self):
        assert extract_neighborhood("София / Център") == "Център"

    def test_with_nbsp(self):
        assert extract_neighborhood("гр. София /\xa0кв. Лозенец") == "Лозенец"

    def test_no_neighborhood(self):
        assert extract_neighborhood("гр. София") == ""

    def test_empty(self):
        assert extract_neighborhood("") == ""


class TestExtractArea:
    def test_standard_format(self):
        assert extract_area("Площ: 95.5 м²") == "95.5"

    def test_with_comma(self):
        assert extract_area("Площ: 95,5 м²") == "95.5"

    def test_integer(self):
        assert extract_area("Площ: 100 м²") == "100"

    def test_no_match(self):
        assert extract_area("No area here") == ""

    def test_empty(self):
        assert extract_area("") == ""


class TestExtractFloor:
    def test_standard_floor(self):
        assert extract_floor("Етаж: 3") == "3"

    def test_parter(self):
        assert extract_floor("Етаж: партер") == "партер"

    def test_last_floor(self):
        assert extract_floor("Етаж: последен") == "последен"

    def test_no_match(self):
        assert extract_floor("No floor here") == ""

    def test_empty(self):
        assert extract_floor("") == ""


class TestExtractRefFromContactUrl:
    def test_standard_ref(self):
        assert extract_ref_from_contact_url("/agent-contact?ref_no=SOF 109946") == "SOF 109946"

    def test_ref_with_ampersand(self):
        assert extract_ref_from_contact_url("/agent?ref_no=ABC123&other=value") == "ABC123"

    def test_no_ref(self):
        assert extract_ref_from_contact_url("/agent-contact") == ""

    def test_empty(self):
        assert extract_ref_from_contact_url("") == ""


class TestExtractOfferTypeFromUrl:
    def test_prodajba(self):
        assert extract_offer_type_from_url("/prodajba-imot-sofia.html") == "продава"

    def test_za_prodajba(self):
        assert extract_offer_type_from_url("/za-prodajba-apartament.html") == "продава"

    def test_naem(self):
        assert extract_offer_type_from_url("/naem-imot-sofia.html") == "наем"

    def test_pod_naem(self):
        assert extract_offer_type_from_url("/pod-naem-apartament.html") == "наем"

    def test_no_match(self):
        assert extract_offer_type_from_url("/imot-sofia.html") == ""

    def test_empty(self):
        assert extract_offer_type_from_url("") == ""


class TestCalculatePricePerM2:
    def test_standard_calculation(self):
        raw = {"price_text": "185 000 €", "details_text": "Площ: 100 м²"}
        assert calculate_price_per_m2(raw) == "1850.0"

    def test_with_decimal_area(self):
        raw = {"price_text": "185 000 €", "details_text": "Площ: 95.5 м²"}
        # 185000 / 95.5 = 1937.17...
        result = float(calculate_price_per_m2(raw))
        assert 1937 < result < 1938

    def test_missing_price(self):
        raw = {"price_text": "", "details_text": "Площ: 100 м²"}
        assert calculate_price_per_m2(raw) == ""

    def test_missing_area(self):
        raw = {"price_text": "185 000 €", "details_text": ""}
        assert calculate_price_per_m2(raw) == ""

    def test_zero_area(self):
        raw = {"price_text": "185 000 €", "details_text": "Площ: 0 м²"}
        assert calculate_price_per_m2(raw) == ""

    def test_empty_raw(self):
        assert calculate_price_per_m2({}) == ""

    def test_invalid_price(self):
        raw = {"price_text": "по договаряне", "details_text": "Площ: 100 м²"}
        assert calculate_price_per_m2(raw) == ""


class TestSuprimmoParserConfig:
    def test_config_values(self):
        parser = SuprimmoParser()
        assert parser.config.name == "suprimmo"
        assert parser.config.base_url == "https://www.suprimmo.bg"
        assert parser.config.encoding == "windows-1251"
        assert parser.config.rate_limit_seconds == 1.5


class TestSuprimmoParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://suprimmo.bg/sofia/apartments", "name": "Sofia Apartments"},
                {"url": "https://suprimmo.bg/plovdiv/houses", "name": "Plovdiv Houses"},
            ]
        }
        urls = SuprimmoParser.build_urls(config)
        assert urls == [
            {"url": "https://suprimmo.bg/sofia/apartments", "name": "Sofia Apartments"},
            {"url": "https://suprimmo.bg/plovdiv/houses", "name": "Plovdiv Houses"},
        ]

    def test_build_urls_empty(self):
        assert SuprimmoParser.build_urls({}) == []


class TestSuprimmoParserExtractListings:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

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
        assert listings[0]["title"] == "Тристаен апартамент"

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "София" in listings[0]["location"]
        assert "Лозенец" in listings[0]["location"]

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "/prodajba-imot-apartament-sofia-lozenets-123456.html"

    def test_extract_listing_details_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "95.5" in listings[0]["details_text"]
        assert "3" in listings[0]["details_text"]

    def test_extract_listing_ref_no(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["ref_no"] == "SOF 109946"

    def test_extract_listing_offer_type_from_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["offer_type"] == "продава"

    def test_extract_listing_offer_type_naem(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[1]["offer_type"] == "наем"

    def test_extract_listing_num_photos(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["num_photos"] == 3
        assert listings[1]["num_photos"] == 1

    def test_extract_listing_agency_name(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency_name"] == "Suprimmo"

    def test_extract_listing_total_offers(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["total_offers"] == 1448
        assert listings[1]["total_offers"] == 1448  # Same for all listings on page

    def test_extract_listing_price_per_m2(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        # First listing: 185000 / 95.5 = 1937.17...
        price_per_m2 = float(listings[0]["price_per_m2"])
        assert 1937 < price_per_m2 < 1938


class TestSuprimmoParserTransform:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    def test_transform_listing(self, parser):
        raw = {
            "price_text": "185 000 €",
            "title": "Тристаен апартамент",
            "location": "гр. София / кв. Лозенец",
            "details_text": "Площ: 95.5 м² Етаж: 3",
            "description": "",
            "details_url": "/prodajba-imot-sofia-123456.html",
            "ref_no": "SOF 109946",
            "offer_type": "продава",
            "agency_name": "Suprimmo",
            "num_photos": 5,
        }
        result = parser.transform_listing(raw)

        assert result.site == "suprimmo"
        assert result.price == 185000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "тристаен"
        assert result.offer_type == "продава"
        assert result.area == "95.5"
        assert result.floor == "3"
        assert result.ref_no == "SOF 109946"
        # Suprimmo doesn't prepend base URL (no prepend_url=True on Field)
        assert result.details_url == "/prodajba-imot-sofia-123456.html"

    def test_transform_listing_bgn(self, parser):
        raw = {
            "price_text": "250 000 лв.",
            "title": "Двустаен апартамент",
            "location": "гр. Пловдив / кв. Център",
            "details_text": "Площ: 65 м²",
            "description": "",
            "details_url": "/imot-plovdiv.html",
            "ref_no": "PLV123",
            "offer_type": "продава",
            "agency_name": "Suprimmo",
            "num_photos": 0,
        }
        result = parser.transform_listing(raw)

        assert result.price == 250000.0
        assert result.currency == "BGN"

    def test_transform_listing_rent(self, parser):
        raw = {
            "price_text": "500 €",
            "title": "Двустаен апартамент",
            "location": "гр. София / кв. Център",
            "details_text": "Площ: 65 м² Етаж: партер",
            "description": "",
            "details_url": "/pod-naem-imot.html",
            "ref_no": "",
            "offer_type": "наем",
            "agency_name": "Suprimmo",
            "num_photos": 1,
        }
        result = parser.transform_listing(raw)

        assert result.offer_type == "наем"
        assert result.floor == "партер"

    def test_transform_listing_with_new_fields(self, parser):
        raw = {
            "price_text": "185 000 €",
            "title": "Тристаен апартамент",
            "location": "гр. София / кв. Лозенец",
            "details_text": "Площ: 95.5 м² Етаж: 3",
            "description": "",
            "details_url": "/prodajba-imot-sofia-123456.html",
            "ref_no": "SOF 109946",
            "offer_type": "продава",
            "agency_name": "Suprimmo",
            "num_photos": 5,
            "total_offers": 1448,
            "price_per_m2": "1937.17",
        }
        result = parser.transform_listing(raw)

        assert result.total_offers == 1448
        assert result.price_per_m2 == "1937.17"


class TestSuprimmoParserPagination:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    def test_get_total_pages_with_page_count(self, parser):
        html = """
        <html>
        <body>
        <p class="font-medium font-semibold">1448 намерени оферти / Страницa 1 от 61</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = parser.get_total_pages(soup)
        assert total == 61

    def test_get_total_pages_with_next_link_fallback(self, parser):
        html = """
        <html>
        <head>
            <link rel="next" href="https://www.suprimmo.bg/page/2/"/>
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = parser.get_total_pages(soup)
        assert total == parser.config.max_pages  # Returns max when next link exists but no page count

    def test_get_total_pages_no_next_link(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        total = parser.get_total_pages(soup)
        assert total == 1

    def test_get_next_page_url_page_2(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/"
        next_url = parser.get_next_page_url(soup, url, 2)
        # Uses the rel="next" link from the HTML
        assert next_url == "https://www.suprimmo.bg/sofia/apartments/page/2/"

    def test_get_next_page_url_page_3(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/page/2/"
        next_url = parser.get_next_page_url(soup, url, 3)
        assert next_url == "https://www.suprimmo.bg/sofia/apartments/page/3/"

    def test_get_next_page_url_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/"
        next_url = parser.get_next_page_url(soup, url, 2)
        assert next_url is None

    def test_get_next_page_url_no_next_link_stops_pagination(self, parser):
        # When there's no rel="next" link, we're on the last page - should return None
        html = """
        <html>
        <head></head>
        <body>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
        </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/page/16/"
        next_url = parser.get_next_page_url(soup, url, 17)
        assert next_url is None


class TestSuprimmoParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    def test_extract_total_offers(self, parser):
        html = """
        <html>
        <body>
        <p class="font-medium font-semibold">1448 намерени оферти / Страницa 1 от 61</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = parser._extract_total_offers(soup)
        assert total == 1448

    def test_extract_total_offers_no_count(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        total = parser._extract_total_offers(soup)
        assert total == 0

    def test_extract_total_offers_different_format(self, parser):
        html = """
        <html>
        <body>
        <p class="font-medium font-semibold">25 намерени оферти</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = parser._extract_total_offers(soup)
        assert total == 25

    def test_extract_listings_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, parser):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="prc">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["title"] == ""

    def test_extract_listing_missing_price(self, parser):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == ""

    def test_extract_listing_missing_location(self, parser):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
            <div class="prc">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == ""

    def test_extract_listing_fallback_ref_from_prop_id(self, parser):
        html = """
        <div class="panel rel shadow offer" data-prop-id="999888">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
            <div class="prc">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["ref_no"] == "999888"

    def test_extract_listing_fallback_url_from_button(self, parser):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <div class="foot">
                <a class="button" href="/imot-456.html">Details</a>
            </div>
            <div class="ttl">Апартамент</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "/imot-456.html"

    def test_extract_listing_no_photos(self, parser):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["num_photos"] == 0

    def test_transform_missing_location(self, parser):
        raw = {
            "price_text": "100 €",
            "title": "Test",
            "location": "",
            "details_text": "",
            "description": "",
            "details_url": "/imot.html",
            "ref_no": "",
            "offer_type": "",
            "agency_name": "Suprimmo",
            "num_photos": 0,
        }
        result = parser.transform_listing(raw)
        assert result.city == ""
        assert result.neighborhood == ""

    def test_default_offer_type_from_datalayer(self, parser):
        html = """
        <html>
        <body>
        <script>dataLayer = [{listing_pagetype: "type:'продава'"}];</script>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["offer_type"] == "продава"

    def test_default_offer_type_naem_from_datalayer(self, parser):
        html = """
        <html>
        <body>
        <script>dataLayer = [{listing_pagetype: "type:'наем'"}];</script>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["offer_type"] == "наем"
