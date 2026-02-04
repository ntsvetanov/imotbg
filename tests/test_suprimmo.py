import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.suprimmo import SuprimmoExtractor

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


class TestTransformerExtractCity:
    """Test city extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_with_prefix_gr(self, transformer):
        city, _ = transformer._parse_location("гр. София / кв. Лозенец")
        assert city == "София"

    def test_with_prefix_s(self, transformer):
        city, _ = transformer._parse_location("с. Панчарево")
        assert city == "Панчарево"

    def test_without_prefix(self, transformer):
        city, _ = transformer._parse_location("София / Лозенец")
        assert city == "София"

    def test_with_nbsp(self, transformer):
        city, _ = transformer._parse_location("гр.\xa0София / кв. Лозенец")
        assert city == "София"

    def test_empty(self, transformer):
        city, _ = transformer._parse_location("")
        assert city == ""

    def test_none(self, transformer):
        city, _ = transformer._parse_location(None)
        assert city == ""


class TestTransformerExtractNeighborhood:
    """Test neighborhood extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_with_kv_prefix(self, transformer):
        _, neighborhood = transformer._parse_location("гр. София / кв. Лозенец")
        # _parse_location returns raw neighborhood; normalization strips "кв." prefix
        normalized = transformer._normalize_neighborhood(neighborhood, "София")
        assert normalized == "Лозенец"

    def test_without_prefix(self, transformer):
        _, neighborhood = transformer._parse_location("София / Център")
        assert neighborhood == "Център"

    def test_with_nbsp(self, transformer):
        _, neighborhood = transformer._parse_location("гр. София /\xa0кв. Лозенец")
        # _parse_location returns raw neighborhood; normalization strips "кв." prefix
        normalized = transformer._normalize_neighborhood(neighborhood, "София")
        assert normalized == "Лозенец"

    def test_no_neighborhood(self, transformer):
        _, neighborhood = transformer._parse_location("гр. София")
        assert neighborhood == ""

    def test_empty(self, transformer):
        _, neighborhood = transformer._parse_location("")
        assert neighborhood == ""


class TestTransformerExtractArea:
    """Test area extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_standard_format(self, transformer):
        assert transformer._extract_area("Площ: 95.5 м²") == 95.5

    def test_with_comma(self, transformer):
        assert transformer._extract_area("Площ: 95,5 м²") == 95.5

    def test_integer(self, transformer):
        assert transformer._extract_area("Площ: 100 м²") == 100.0

    def test_no_match(self, transformer):
        assert transformer._extract_area("No area here") is None

    def test_empty(self, transformer):
        assert transformer._extract_area("") is None


class TestTransformerExtractFloor:
    """Test floor extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_standard_floor(self, transformer):
        assert transformer._extract_floor("Етаж: 3") == "3"

    def test_parter(self, transformer):
        assert transformer._extract_floor("Етаж: партер") == "партер"

    def test_last_floor(self, transformer):
        assert transformer._extract_floor("Етаж: последен") == "последен"

    def test_no_match(self, transformer):
        assert transformer._extract_floor("No floor here") == ""

    def test_empty(self, transformer):
        assert transformer._extract_floor("") == ""


class TestTransformerExtractOfferType:
    """Test offer type extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_prodajba(self, transformer):
        result = transformer._extract_offer_type("", "/prodajba-imot-sofia.html")
        assert result == "продава"

    def test_za_prodajba(self, transformer):
        result = transformer._extract_offer_type("", "/za-prodajba-apartament.html")
        assert result == "продава"

    def test_naem(self, transformer):
        result = transformer._extract_offer_type("", "/naem-imot-sofia.html")
        assert result == "наем"

    def test_pod_naem(self, transformer):
        result = transformer._extract_offer_type("", "/pod-naem-apartament.html")
        assert result == "наем"

    def test_no_match(self, transformer):
        url = "/imot-sofia.html"
        result = transformer._extract_offer_type("", url)
        assert result == ""

    def test_empty(self, transformer):
        result = transformer._extract_offer_type("", "")
        assert result == ""


class TestTransformerCalculatePricePerM2:
    """Test price per m2 calculation via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_standard_calculation(self, transformer):
        # 185000 EUR / 100 m2 = 1850.0
        result = transformer._calculate_price_per_m2(185000.0, 100.0)
        assert result == 1850.0

    def test_with_decimal_area(self, transformer):
        # 185000 / 95.5 = 1937.17...
        result = transformer._calculate_price_per_m2(185000.0, 95.5)
        assert 1937 < result < 1938

    def test_missing_price(self, transformer):
        result = transformer._calculate_price_per_m2(None, 100.0)
        assert result is None

    def test_missing_area(self, transformer):
        result = transformer._calculate_price_per_m2(185000.0, None)
        assert result is None

    def test_zero_area(self, transformer):
        result = transformer._calculate_price_per_m2(185000.0, 0)
        assert result is None

    def test_invalid_price(self, transformer):
        # Price parsing happens before calculate_price_per_m2, so None is passed
        result = transformer._calculate_price_per_m2(None, 100.0)
        assert result is None


class TestSuprimmoExtractorConfig:
    def test_config_values(self):
        extractor = SuprimmoExtractor()
        assert extractor.config.name == "suprimmo"
        assert extractor.config.base_url == "https://www.suprimmo.bg"
        assert extractor.config.encoding == "windows-1251"
        assert extractor.config.rate_limit_seconds == 1.5


class TestSuprimmoExtractorBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://suprimmo.bg/sofia/apartments", "name": "Sofia Apartments"},
                {"url": "https://suprimmo.bg/plovdiv/houses", "name": "Plovdiv Houses"},
            ]
        }
        urls = SuprimmoExtractor.build_urls(config)
        assert urls == [
            {"url": "https://suprimmo.bg/sofia/apartments", "name": "Sofia Apartments"},
            {"url": "https://suprimmo.bg/plovdiv/houses", "name": "Plovdiv Houses"},
        ]

    def test_build_urls_empty(self):
        assert SuprimmoExtractor.build_urls({}) == []


class TestSuprimmoExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return SuprimmoExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "185 000 €" in listings[0].price_text

    def test_extract_listing_title(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "Тристаен апартамент" in listings[0].title

    def test_extract_listing_location(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "София" in listings[0].location_text
        assert "Лозенец" in listings[0].location_text

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].details_url == "/prodajba-imot-apartament-sofia-lozenets-123456.html"

    def test_extract_listing_area_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "95" in listings[0].area_text

    def test_extract_listing_ref_no(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        # ref_no is now taken from data-prop-id attribute
        assert listings[0].ref_no == "123456"

    def test_extract_listing_num_photos(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 3
        assert listings[1].num_photos == 1

    def test_extract_listing_agency_name(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == "Suprimmo"

    def test_extract_listing_total_offers(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_offers == 1448
        assert listings[1].total_offers == 1448  # Same for all listings on page


class TestSuprimmoTransform:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="185 000 €",
            title="продава Тристаен апартамент",
            location_text="гр. София / кв. Лозенец",
            area_text="95.5 м²",
            floor_text="3",
            description="",
            details_url="/prodajba-imot-sofia-123456.html",
            ref_no="SOF 109946",
            agency_name="Suprimmo",
            num_photos=5,
        )
        result = transformer.transform(raw)

        assert result.site == "suprimmo"
        assert result.price == 185000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "тристаен"
        assert result.offer_type == "продава"
        assert result.area == 95.5
        assert result.ref_no == "SOF 109946"
        assert result.details_url == "/prodajba-imot-sofia-123456.html"

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="250 000 лв.",
            title="продава Двустаен апартамент",
            location_text="гр. Пловдив / кв. Център",
            area_text="65 м²",
            description="",
            details_url="/imot-plovdiv.html",
            ref_no="PLV123",
            agency_name="Suprimmo",
            num_photos=0,
        )
        result = transformer.transform(raw)

        # 250000 BGN / 1.9558 = 127825.43 EUR
        assert result.price == pytest.approx(127825.43, rel=0.01)
        assert result.original_currency == "BGN"

    def test_transform_listing_rent(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="500 €",
            title="наем Двустаен апартамент",
            location_text="гр. София / кв. Център",
            area_text="65 м²",
            floor_text="Етаж: партер",  # Transformer expects "Етаж: X" format
            description="",
            details_url="/pod-naem-imot.html",
            ref_no="",
            agency_name="Suprimmo",
            num_photos=1,
        )
        result = transformer.transform(raw)

        assert result.offer_type == "наем"
        assert result.floor == "партер"

    def test_transform_listing_with_total_offers(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="185 000 €",
            title="продава Тристаен апартамент",
            location_text="гр. София / кв. Лозенец",
            area_text="95.5 м²",
            floor_text="3",
            description="",
            details_url="/prodajba-imot-sofia-123456.html",
            ref_no="SOF 109946",
            agency_name="Suprimmo",
            num_photos=5,
            total_offers=1448,
        )
        result = transformer.transform(raw)

        assert result.total_offers == 1448
        # Price per m2: 185000 / 95.5 = 1937.17
        assert result.price_per_m2 == pytest.approx(1937.17, rel=0.01)

    def test_transform_listing_with_search_url(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="185 000 €",
            title="продава Тристаен апартамент",
            location_text="гр. София / кв. Лозенец",
            area_text="95.5 м²",
            floor_text="3",
            description="",
            details_url="/prodajba-imot-sofia-123456.html",
            ref_no="SOF 109946",
            agency_name="Suprimmo",
            num_photos=5,
            total_offers=1448,
            search_url="https://www.suprimmo.bg/sofia/apartments/",
        )
        result = transformer.transform(raw)

        assert result.search_url == "https://www.suprimmo.bg/sofia/apartments/"


class TestSuprimmoExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return SuprimmoExtractor()

    def test_get_total_pages_with_page_count(self, extractor):
        html = """
        <html>
        <body>
        <p class="font-medium font-semibold">1448 намерени оферти / Страницa 1 от 61</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = extractor.get_total_pages(soup)
        assert total == 61

    def test_get_total_pages_with_next_link_fallback(self, extractor):
        html = """
        <html>
        <head>
            <link rel="next" href="https://www.suprimmo.bg/page/2/"/>
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = extractor.get_total_pages(soup)
        assert total == extractor.config.max_pages  # Returns max when next link exists but no page count

    def test_get_total_pages_no_next_link(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        total = extractor.get_total_pages(soup)
        assert total == 1

    def test_get_next_page_url_page_2(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/"
        next_url = extractor.get_next_page_url(soup, url, 2)
        # Uses the rel="next" link from the HTML
        assert next_url == "https://www.suprimmo.bg/sofia/apartments/page/2/"

    def test_get_next_page_url_page_3(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/page/2/"
        next_url = extractor.get_next_page_url(soup, url, 3)
        assert next_url == "https://www.suprimmo.bg/sofia/apartments/page/3/"

    def test_get_next_page_url_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.suprimmo.bg/sofia/apartments/"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert next_url is None

    def test_get_next_page_url_no_next_link_stops_pagination(self, extractor):
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
        next_url = extractor.get_next_page_url(soup, url, 17)
        assert next_url is None


class TestSuprimmoExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return SuprimmoExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_total_offers(self, extractor):
        html = """
        <html>
        <body>
        <p class="font-medium font-semibold">1448 намерени оферти / Страницa 1 от 61</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = extractor._extract_total_offers(soup)
        assert total == 1448

    def test_extract_total_offers_no_count(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        total = extractor._extract_total_offers(soup)
        assert total == 0

    def test_extract_total_offers_different_format(self, extractor):
        html = """
        <html>
        <body>
        <p class="font-medium font-semibold">25 намерени оферти</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = extractor._extract_total_offers(soup)
        assert total == 25

    def test_extract_listings_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, extractor):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="prc">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].title == ""

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == ""

    def test_extract_listing_missing_location(self, extractor):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
            <div class="prc">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == ""

    def test_extract_listing_fallback_ref_from_prop_id(self, extractor):
        html = """
        <div class="panel rel shadow offer" data-prop-id="999888">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
            <div class="prc">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].ref_no == "999888"

    def test_extract_listing_fallback_url_from_button(self, extractor):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <div class="foot">
                <a class="button" href="/imot-456.html">Details</a>
            </div>
            <div class="ttl">Апартамент</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].details_url == "/imot-456.html"

    def test_extract_listing_no_photos(self, extractor):
        html = """
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 0

    def test_transform_missing_location(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="100 €",
            title="Test",
            location_text="",
            description="",
            details_url="/imot.html",
            ref_no="",
            agency_name="Suprimmo",
            num_photos=0,
        )
        result = transformer.transform(raw)
        assert result.city == ""
        assert result.neighborhood == ""

    def test_default_offer_type_from_datalayer(self, extractor):
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
        listings = list(extractor.extract_listings(soup))
        # The title should have offer type prepended
        assert "продава" in listings[0].title

    def test_default_offer_type_naem_from_datalayer(self, extractor):
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
        listings = list(extractor.extract_listings(soup))
        # The title should have offer type prepended
        assert "наем" in listings[0].title


class TestSuprimmoExtractorNewFields:
    """Test extraction of new fields: total_floors_text and raw_link_description."""

    @pytest.fixture
    def extractor(self):
        return SuprimmoExtractor()

    def test_extract_total_floors_text(self, extractor):
        html = """
        <html><body>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html" title="Test Title">Link</a>
            <div class="ttl">Апартамент</div>
            <div class="lst"><b>Площ: </b><i>68.68 м²</i><b>Етаж:</b><i> 3</i><b>Етажност на сградата:</b><i> 4</i></div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == "4"
        assert listings[0].floor_text == "3"

    def test_extract_raw_link_description(self, extractor):
        html = """
        <html><body>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html" title="Тристаен апартамент в Лозенец - SUPRIMMO">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == "Тристаен апартамент в Лозенец - SUPRIMMO"

    def test_extract_raw_link_description_missing(self, extractor):
        html = """
        <html><body>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == ""

    def test_extract_total_floors_text_missing(self, extractor):
        html = """
        <html><body>
        <div class="panel rel shadow offer" data-prop-id="123">
            <a class="lnk" href="/imot.html">Link</a>
            <div class="ttl">Апартамент</div>
            <div class="lst">Площ: 95.5 м² Етаж: 3</div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == ""


class TestSuprimmoTransformTotalFloors:
    """Test transformer handling of total_floors field."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_with_total_floors(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="185 000 €",
            title="продава Тристаен апартамент",
            location_text="гр. София / кв. Лозенец",
            area_text="95.5 м²",
            floor_text="3",
            total_floors_text="8",
            description="",
            details_url="/prodajba-imot-sofia-123456.html",
            ref_no="SOF 109946",
            agency_name="Suprimmo",
            num_photos=5,
        )
        result = transformer.transform(raw)

        assert result.floor == "3"
        assert result.total_floors == "8"

    def test_transform_without_total_floors(self, transformer):
        raw = RawListing(
            site="suprimmo",
            price_text="185 000 €",
            title="продава Тристаен апартамент",
            location_text="гр. София / кв. Лозенец",
            area_text="95.5 м²",
            floor_text="3",
            description="",
            details_url="/prodajba-imot-sofia-123456.html",
            ref_no="SOF 109946",
            agency_name="Suprimmo",
            num_photos=5,
        )
        result = transformer.transform(raw)

        assert result.floor == "3"
        assert result.total_floors is None
