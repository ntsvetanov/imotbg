"""Tests for the AloBgParser."""

import pytest
from bs4 import BeautifulSoup

from src.sites.alobg import (
    AloBgParser,
    extract_alo_city,
    extract_alo_neighborhood,
    extract_ref_from_url,
    _calculate_listing_price_per_m2,
)


# Sample HTML for testing
SAMPLE_LISTING_HTML = """
<div class="listtop-item">
    <a href="/obiava/12345">
        <h3 class="listtop-item-title">Продава двустаен апартамент</h3>
    </a>
    <img class="listtop-item-photo" src="photo1.jpg"/>
    <img class="listtop-item-photo" src="photo2.jpg"/>
    <div class="listtop-item-address"><i>Лозенец, София</i></div>
    <div class="ads-params-row">
        <div class="ads-param-title">Цена</div>
        <div class="ads-params-cell"><span class="ads-params-single">150 000 EUR</span></div>
    </div>
    <div class="ads-params-row">
        <div class="ads-param-title">Вид на имота</div>
        <div class="ads-params-cell"><span class="ads-params-single">Двустаен апартамент</span></div>
    </div>
    <div class="ads-params-row">
        <div class="ads-param-title">Квадратура</div>
        <div class="ads-params-cell"><span class="ads-params-single">65 кв.м.</span></div>
    </div>
    <div class="ads-params-row">
        <div class="ads-param-title">Номер на етажа</div>
        <div class="ads-params-cell"><span class="ads-params-single">3</span></div>
    </div>
    <div class="listtop-desc">Просторен двустаен апартамент в центъра.</div>
    <div class="listtop-publisher"><span>Агенция Имоти</span></div>
</div>
"""

SAMPLE_VIP_LISTING_HTML = """
<div class="listvip-item">
    <a href="/obiava/67890">
        <h3 class="listvip-item-title">Под наем тристаен апартамент</h3>
    </a>
    <img class="listvip-item-photo" src="photo1.jpg"/>
    <div class="listvip-item-address"><i>Център, Пловдив</i></div>
    <span class="ads-params-multi" title="Цена">800 EUR</span>
    <span class="ads-params-multi" title="Вид на имота">Тристаен апартамент</span>
    <span class="ads-params-multi" title="Квадратура">90 кв.м.</span>
    <div class="listvip-desc">Светъл апартамент с гледка към града.</div>
    <div class="listvip-publisher"><span>Частно лице</span></div>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
    <div class="search-results-count">Намерени 1500 обяви</div>
    {SAMPLE_LISTING_HTML}
    {SAMPLE_VIP_LISTING_HTML}
    <div class="my-paginator">
        <a href="?page=1">1</a>
        <a href="?page=2">2</a>
        <a href="?page=3">3</a>
        <a href="?page=4">4</a>
        <a href="?page=5">5</a>
    </div>
</body>
</html>
"""

SAMPLE_EMPTY_PAGE_HTML = """
<html>
<body>
    <div class="no-results">Няма намерени обяви</div>
</body>
</html>
"""


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestExtractAloCity:
    def test_extract_city_from_location(self):
        """City is last part after comma."""
        assert extract_alo_city("Лозенец, София") == "София"

    def test_extract_city_from_location_plovdiv(self):
        """City extraction works for other cities."""
        assert extract_alo_city("Център, Пловдив") == "Пловдив"

    def test_extract_city_single_part(self):
        """Single part location returns that part as city."""
        result = extract_alo_city("София")
        assert result == "София"

    def test_extract_city_empty(self):
        """Empty location returns empty string."""
        assert extract_alo_city("") == ""

    def test_extract_city_none(self):
        """None location returns empty string."""
        assert extract_alo_city(None) == ""

    def test_extract_city_multiple_parts(self):
        """Multiple commas - city is still last part."""
        assert extract_alo_city("ж.к. Младост 1, кв. Младост, София") == "София"


class TestExtractAloNeighborhood:
    def test_extract_neighborhood(self):
        """Neighborhood is first part before comma."""
        assert extract_alo_neighborhood("Лозенец, София") == "Лозенец"

    def test_extract_neighborhood_plovdiv(self):
        """Neighborhood extraction for Plovdiv."""
        assert extract_alo_neighborhood("Център, Пловдив") == "Център"

    def test_extract_neighborhood_single_part(self):
        """Single part location returns empty (no neighborhood)."""
        assert extract_alo_neighborhood("София") == ""

    def test_extract_neighborhood_empty(self):
        """Empty location returns empty string."""
        assert extract_alo_neighborhood("") == ""

    def test_extract_neighborhood_none(self):
        """None location returns empty string."""
        assert extract_alo_neighborhood(None) == ""


class TestExtractRefFromUrl:
    def test_extract_ref_standard(self):
        """Extract reference from standard URL."""
        assert extract_ref_from_url("/obiava/12345-test") == "12345"

    def test_extract_ref_no_match(self):
        """Returns empty when no match."""
        assert extract_ref_from_url("/search/imoti") == ""

    def test_extract_ref_empty(self):
        """Empty URL returns empty string."""
        assert extract_ref_from_url("") == ""

    def test_extract_ref_none(self):
        """None URL returns empty string."""
        assert extract_ref_from_url(None) == ""


class TestCalculatePricePerM2:
    def test_calculate_price_per_m2_standard(self):
        """Calculate price per m2 for standard case."""
        raw = {"price_text": "150 000 EUR", "area_text": "100 кв.м."}
        assert _calculate_listing_price_per_m2(raw) == "1500.0"

    def test_calculate_price_per_m2_with_decimal(self):
        """Calculate price per m2 with decimal area."""
        raw = {"price_text": "150 000 EUR", "area_text": "65 кв.м."}
        result = float(_calculate_listing_price_per_m2(raw))
        assert 2307 < result < 2308

    def test_calculate_price_per_m2_no_price(self):
        """Returns empty when no price."""
        raw = {"price_text": "", "area_text": "65 кв.м."}
        assert _calculate_listing_price_per_m2(raw) == ""

    def test_calculate_price_per_m2_no_area(self):
        """Returns empty when no area."""
        raw = {"price_text": "150 000 EUR", "area_text": ""}
        assert _calculate_listing_price_per_m2(raw) == ""

    def test_calculate_price_per_m2_empty(self):
        """Returns empty for empty dict."""
        assert _calculate_listing_price_per_m2({}) == ""


# =============================================================================
# Parser Config Tests
# =============================================================================


class TestAloBgParserConfig:
    @pytest.fixture
    def parser(self):
        return AloBgParser()

    def test_config_name(self, parser):
        assert parser.config.name == "alobg"

    def test_config_base_url(self, parser):
        assert parser.config.base_url == "https://www.alo.bg"

    def test_config_encoding(self, parser):
        assert parser.config.encoding == "utf-8"

    def test_config_rate_limit(self, parser):
        assert parser.config.rate_limit_seconds == 1.5


# =============================================================================
# Extract Listings Tests
# =============================================================================


class TestAloBgParserExtractListings:
    @pytest.fixture
    def parser(self):
        return AloBgParser()

    def test_extract_listtop_listing(self, parser):
        """Test extracting regular (listtop) listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert len(listings) == 1
        listing = listings[0]
        assert listing["title"] == "Продава двустаен апартамент"
        assert listing["details_url"] == "/obiava/12345"
        assert listing["location"] == "Лозенец, София"
        assert listing["price_text"] == "150 000 EUR"
        assert listing["property_type_text"] == "Двустаен апартамент"
        assert listing["area_text"] == "65 кв.м."
        assert listing["floor_text"] == "3"
        assert listing["description"] == "Просторен двустаен апартамент в центъра."
        assert listing["agency_name"] == "Агенция Имоти"

    def test_extract_listvip_listing(self, parser):
        """Test extracting VIP listing (uses different selectors)."""
        soup = BeautifulSoup(SAMPLE_VIP_LISTING_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert len(listings) == 1
        listing = listings[0]
        assert listing["title"] == "Под наем тристаен апартамент"
        assert listing["details_url"] == "/obiava/67890"
        assert listing["location"] == "Център, Пловдив"
        assert listing["price_text"] == "800 EUR"
        assert listing["property_type_text"] == "Тристаен апартамент"
        assert listing["area_text"] == "90 кв.м."

    def test_extract_multiple_listings(self, parser):
        """Test extracting multiple listings from page."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert len(listings) == 2

    def test_extract_listing_ref_no(self, parser):
        """Test extracting reference number from listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert listings[0]["ref_no"] == "12345"

    def test_extract_listing_num_photos(self, parser):
        """Test extracting photo count from listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert listings[0]["num_photos"] == 2  # 2 listtop-item-photo images

    def test_extract_listing_total_offers(self, parser):
        """Test extracting total offers from page."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert listings[0]["total_offers"] == 1500
        assert listings[1]["total_offers"] == 1500  # Same for all listings

    def test_extract_listing_price_per_m2(self, parser):
        """Test extracting price per m2 from listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        # 150000 / 65 = 2307.69...
        price_per_m2 = float(listings[0]["price_per_m2"])
        assert 2307 < price_per_m2 < 2308

    def test_extract_no_listings(self, parser):
        """Test empty page returns no listings."""
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        listings = list(parser.extract_listings(soup))

        assert len(listings) == 0


# =============================================================================
# Transform Listing Tests
# =============================================================================


class TestAloBgParserTransformListing:
    @pytest.fixture
    def parser(self):
        return AloBgParser()

    def test_transform_listing_sale(self, parser):
        """Test transforming a sale listing."""
        raw = {
            "title": "Продава двустаен апартамент",
            "details_url": "/obiava/12345",
            "location": "Лозенец, София",
            "price_text": "150 000 EUR",
            "property_type_text": "Двустаен апартамент",
            "area_text": "65 кв.м.",
            "floor_text": "3",
            "description": "Описание",
            "agency_name": "Агенция Имоти",
        }
        result = parser.transform_listing(raw)

        assert result.site == "alobg"
        assert result.price == 150000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.area == "65 кв.м."
        assert result.floor == "3"
        assert result.details_url == "https://www.alo.bg/obiava/12345"

    def test_transform_listing_rent(self, parser):
        """Test transforming a rent listing."""
        raw = {
            "title": "Под наем тристаен апартамент",
            "details_url": "/obiava/67890",
            "location": "Център, Пловдив",
            "price_text": "800 EUR",
            "property_type_text": "Тристаен апартамент",
            "area_text": "90 кв.м.",
            "floor_text": "5",
            "description": "",
            "agency_name": "",
        }
        result = parser.transform_listing(raw)

        assert result.site == "alobg"
        assert result.price == 800.0
        assert result.currency == "EUR"
        assert result.city == "Пловдив"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"
        assert result.offer_type == "наем"

    def test_transform_listing_bgn(self, parser):
        """Test transforming a listing with BGN price."""
        raw = {
            "title": "Продава мезонет",
            "details_url": "/obiava/111",
            "location": "Витоша, София",
            "price_text": "250 000 лв.",
            "property_type_text": "Мезонет",
            "area_text": "120 кв.м.",
            "floor_text": "",
            "description": "",
            "agency_name": "",
        }
        result = parser.transform_listing(raw)

        assert result.price == 250000.0
        assert result.currency == "BGN"
        assert result.property_type == "мезонет"

    def test_transform_listing_prepends_base_url(self, parser):
        """Test that details_url is prepended with base URL."""
        raw = {
            "title": "Test",
            "details_url": "/obiava/999",
            "location": "",
            "price_text": "",
            "property_type_text": "",
            "area_text": "",
            "floor_text": "",
            "description": "",
            "agency_name": "",
        }
        result = parser.transform_listing(raw)

        assert result.details_url == "https://www.alo.bg/obiava/999"

    def test_transform_listing_with_new_fields(self, parser):
        """Test transforming a listing with new fields."""
        raw = {
            "title": "Продава двустаен апартамент",
            "details_url": "/obiava/12345",
            "location": "Лозенец, София",
            "price_text": "150 000 EUR",
            "property_type_text": "Двустаен апартамент",
            "area_text": "65 кв.м.",
            "floor_text": "3",
            "description": "Описание",
            "agency_name": "Агенция Имоти",
            "ref_no": "12345",
            "num_photos": 5,
            "total_offers": 1500,
            "price_per_m2": "2307.69",
        }
        result = parser.transform_listing(raw)

        assert result.ref_no == "12345"
        assert result.num_photos == 5
        assert result.total_offers == 1500
        assert result.price_per_m2 == "2307.69"

    def test_transform_listing_with_search_url(self, parser):
        """Test transforming a listing with search_url."""
        raw = {
            "title": "Продава двустаен апартамент",
            "details_url": "/obiava/12345",
            "location": "Лозенец, София",
            "price_text": "150 000 EUR",
            "property_type_text": "Двустаен апартамент",
            "area_text": "65 кв.м.",
            "floor_text": "3",
            "description": "Описание",
            "agency_name": "Агенция Имоти",
            "ref_no": "12345",
            "num_photos": 5,
            "total_offers": 1500,
            "price_per_m2": "2307.69",
            "search_url": "https://www.alo.bg/imoti/sofia?type=sale",
        }
        result = parser.transform_listing(raw)

        assert result.search_url == "https://www.alo.bg/imoti/sofia?type=sale"


# =============================================================================
# Pagination Tests
# =============================================================================


class TestAloBgParserPagination:
    @pytest.fixture
    def parser(self):
        return AloBgParser()

    def test_get_total_pages(self, parser):
        """Test total pages extraction from pagination."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        total = parser.get_total_pages(soup)

        assert total == 5

    def test_get_total_pages_no_pagination(self, parser):
        """Test returns 1 when no pagination exists."""
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        total = parser.get_total_pages(soup)

        assert total == 1

    def test_get_next_page_url_first_page(self, parser):
        """Test getting next page URL from first page."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia?type=sale"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.alo.bg/imoti/sofia?type=sale&page=2"

    def test_get_next_page_url_with_existing_page(self, parser):
        """Test updating existing page parameter."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia?type=sale&page=2"
        next_url = parser.get_next_page_url(soup, url, 3)

        assert next_url == "https://www.alo.bg/imoti/sofia?type=sale&page=3"

    def test_get_next_page_url_beyond_total(self, parser):
        """Test returns None when page exceeds total."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia"
        next_url = parser.get_next_page_url(soup, url, 10)

        assert next_url is None

    def test_get_next_page_url_empty_page(self, parser):
        """Test returns None when page has no listings."""
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url is None


# =============================================================================
# Private Method Tests
# =============================================================================


class TestAloBgParserPrivateMethods:
    @pytest.fixture
    def parser(self):
        return AloBgParser()

    def test_extract_param_value_from_row(self, parser):
        """Test extracting parameter from ads-params-row."""
        html = """
        <div class="item">
            <div class="ads-params-row">
                <div class="ads-param-title">Цена</div>
                <div class="ads-params-cell"><span class="ads-params-single">100 000</span></div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".item")
        result = parser._extract_param_value(item, "Цена")

        assert result == "100 000"

    def test_extract_param_value_from_multi(self, parser):
        """Test extracting parameter from ads-params-multi span."""
        html = """
        <div class="item">
            <span class="ads-params-multi" title="Цена">200 000</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".item")
        result = parser._extract_param_value(item, "Цена")

        assert result == "200 000"

    def test_extract_param_value_not_found(self, parser):
        """Test returns empty string when param not found."""
        html = '<div class="item"></div>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".item")
        result = parser._extract_param_value(item, "Цена")

        assert result == ""

    def test_extract_listing_no_title(self, parser):
        """Test returns None when no title element."""
        html = '<div class="listtop-item"><div>No title here</div></div>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".listtop-item")
        result = parser._extract_listing(item)

        assert result is None

    def test_extract_listing_adds_slash_to_href(self, parser):
        """Test that href without leading slash gets one added."""
        html = """
        <div class="listtop-item">
            <a href="obiava/123">
                <h3 class="listtop-item-title">Test</h3>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".listtop-item")
        result = parser._extract_listing(item)

        assert result["details_url"] == "/obiava/123"
