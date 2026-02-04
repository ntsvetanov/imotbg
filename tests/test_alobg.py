"""Tests for the AloBgExtractor and Transformer integration."""

import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.alobg import AloBgExtractor

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
# Extractor Config Tests
# =============================================================================


class TestAloBgExtractorConfig:
    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    def test_config_name(self, extractor):
        assert extractor.config.name == "alobg"

    def test_config_base_url(self, extractor):
        assert extractor.config.base_url == "https://www.alo.bg"

    def test_config_encoding(self, extractor):
        assert extractor.config.encoding == "utf-8"

    def test_config_rate_limit(self, extractor):
        assert extractor.config.rate_limit_seconds == 1.5


# =============================================================================
# Extract Listings Tests
# =============================================================================


class TestAloBgExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    def test_extract_listtop_listing(self, extractor):
        """Test extracting regular (listtop) listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert len(listings) == 1
        listing = listings[0]
        assert listing.title == "Продава двустаен апартамент"
        assert listing.details_url == "https://www.alo.bg/obiava/12345"
        assert listing.location_text == "Лозенец, София"
        assert listing.price_text == "150 000 EUR"
        assert listing.area_text == "65 кв.м."
        assert listing.floor_text == "3"
        assert listing.description == "Просторен двустаен апартамент в центъра."
        assert listing.agency_name == "Агенция Имоти"

    def test_extract_listvip_listing(self, extractor):
        """Test extracting VIP listing (uses different selectors)."""
        soup = BeautifulSoup(SAMPLE_VIP_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert len(listings) == 1
        listing = listings[0]
        assert listing.title == "Под наем тристаен апартамент"
        assert listing.details_url == "https://www.alo.bg/obiava/67890"
        assert listing.location_text == "Център, Пловдив"
        assert listing.price_text == "800 EUR"
        assert listing.area_text == "90 кв.м."

    def test_extract_multiple_listings(self, extractor):
        """Test extracting multiple listings from page."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert len(listings) == 2

    def test_extract_listing_ref_no(self, extractor):
        """Test extracting reference number from listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert listings[0].ref_no == "12345"

    def test_extract_listing_num_photos(self, extractor):
        """Test extracting photo count from listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert listings[0].num_photos == 2  # 2 listtop-item-photo images

    def test_extract_listing_total_offers(self, extractor):
        """Test extracting total offers from page."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert listings[0].total_offers == 1500
        assert listings[1].total_offers == 1500  # Same for all listings

    def test_extract_no_listings(self, extractor):
        """Test empty page returns no listings."""
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert len(listings) == 0

    def test_extract_listing_site(self, extractor):
        """Test that extracted listing has correct site."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert listings[0].site == "alobg"

    def test_extract_listing_scraped_at(self, extractor):
        """Test that extracted listing has scraped_at timestamp."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert listings[0].scraped_at is not None

    def test_extract_offer_type_from_page_context(self, extractor):
        """Test offer_type is embedded in title from page context when not in title."""
        # HTML with title that doesn't contain offer type, but has canonical URL
        html = """
        <html>
        <head>
            <link rel="canonical" href="https://www.alo.bg/obiavi/imoti-prodajbi/apartamenti/" />
        </head>
        <body>
            <div class="listtop-item">
                <a href="/obiava/12345">
                    <h3 class="listtop-item-title">Двустаен апартамент в центъра</h3>
                </a>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))

        assert len(listings) == 1
        # Offer type should be prepended to title
        assert "продава" in listings[0].title.lower()


# =============================================================================
# Transform Listing Tests (using Transformer)
# =============================================================================


class TestTransformerWithAloBgData:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing_sale(self, transformer):
        """Test transforming a sale listing."""
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
            floor_text="3",
            description="Описание",
            agency_name="Агенция Имоти",
        )
        result = transformer.transform(raw)

        assert result.site == "alobg"
        assert result.price == 150000.0
        assert result.original_currency == "EUR"
        # Note: Transformer parses "X, Y" as city=X, neighborhood=Y
        # For alo.bg format "neighborhood, city", this gets reversed
        # The city "Лозенец" gets normalized to "Лозенец" (recognized as Sofia neighborhood)
        assert result.city == "Лозенец"
        assert result.neighborhood == "София"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.area == 65.0
        # Plain numbers are now recognized as floors
        assert result.floor == "3"
        assert result.details_url == "https://www.alo.bg/obiava/12345"

    def test_transform_listing_rent(self, transformer):
        """Test transforming a rent listing."""
        raw = RawListing(
            site="alobg",
            title="Под наем тристаен апартамент",
            details_url="https://www.alo.bg/obiava/67890",
            location_text="Център, Пловдив",
            price_text="800 EUR",
            area_text="90 кв.м.",
            floor_text="5",
            description="",
            agency_name="",
        )
        result = transformer.transform(raw)

        assert result.site == "alobg"
        assert result.price == 800.0
        assert result.original_currency == "EUR"
        # Note: Transformer parses "X, Y" as city=X, neighborhood=Y
        assert result.city == "Център"
        assert result.neighborhood == "Пловдив"
        assert result.property_type == "тристаен"
        assert result.offer_type == "наем"

    def test_transform_listing_bgn(self, transformer):
        """Test transforming a listing with BGN price."""
        raw = RawListing(
            site="alobg",
            title="Продава мезонет",
            details_url="https://www.alo.bg/obiava/111",
            location_text="Витоша, София",
            price_text="250 000 лв.",
            area_text="120 кв.м.",
            floor_text="",
            description="",
            agency_name="",
        )
        result = transformer.transform(raw)

        # Price should be converted to EUR (250000 / 1.9558)
        assert result.price is not None
        assert 127000 < result.price < 128000  # ~127800 EUR
        assert result.original_currency == "BGN"
        assert result.property_type == "мезонет"

    def test_transform_listing_with_new_fields(self, transformer):
        """Test transforming a listing with additional fields."""
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
            floor_text="3",
            description="Описание",
            agency_name="Агенция Имоти",
            ref_no="12345",
            num_photos=5,
            total_offers=1500,
        )
        result = transformer.transform(raw)

        assert result.ref_no == "12345"
        assert result.num_photos == 5
        assert result.total_offers == 1500

    def test_transform_listing_price_per_m2(self, transformer):
        """Test that price_per_m2 is calculated correctly."""
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
        )
        result = transformer.transform(raw)

        # 150000 / 65 = 2307.69...
        assert result.price_per_m2 is not None
        assert 2307 < result.price_per_m2 < 2308

    def test_transform_listing_with_search_url(self, transformer):
        """Test transforming a listing with search_url."""
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
            floor_text="3",
            description="Описание",
            agency_name="Агенция Имоти",
            ref_no="12345",
            num_photos=5,
            total_offers=1500,
            search_url="https://www.alo.bg/imoti/sofia?type=sale",
        )
        result = transformer.transform(raw)

        assert result.search_url == "https://www.alo.bg/imoti/sofia?type=sale"

    def test_transform_listing_fingerprint(self, transformer):
        """Test that fingerprint is calculated."""
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
        )
        result = transformer.transform(raw)

        assert result.fingerprint_hash != ""


# =============================================================================
# Pagination Tests
# =============================================================================


class TestAloBgExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    def test_get_total_pages(self, extractor):
        """Test total pages extraction from pagination."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        total = extractor.get_total_pages(soup)

        assert total == 5

    def test_get_total_pages_no_pagination(self, extractor):
        """Test returns 1 when no pagination exists."""
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        total = extractor.get_total_pages(soup)

        assert total == 1

    def test_get_next_page_url_first_page(self, extractor):
        """Test getting next page URL from first page."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia?type=sale"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.alo.bg/imoti/sofia?type=sale&page=2"

    def test_get_next_page_url_with_existing_page(self, extractor):
        """Test updating existing page parameter."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia?type=sale&page=2"
        next_url = extractor.get_next_page_url(soup, url, 3)

        assert next_url == "https://www.alo.bg/imoti/sofia?type=sale&page=3"

    def test_get_next_page_url_beyond_total(self, extractor):
        """Test returns None when page exceeds total."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia"
        next_url = extractor.get_next_page_url(soup, url, 10)

        assert next_url is None

    def test_get_next_page_url_empty_page(self, extractor):
        """Test returns None when page has no listings."""
        soup = BeautifulSoup(SAMPLE_EMPTY_PAGE_HTML, "html.parser")
        url = "https://www.alo.bg/imoti/sofia"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url is None


# =============================================================================
# Private Method Tests
# =============================================================================


class TestAloBgExtractorPrivateMethods:
    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    def test_get_param_value_from_row(self, extractor):
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
        result = extractor._get_param_value(item, "Цена")

        assert result == "100 000"

    def test_get_param_value_from_multi(self, extractor):
        """Test extracting parameter from ads-params-multi span."""
        html = """
        <div class="item">
            <span class="ads-params-multi" title="Цена">200 000</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".item")
        result = extractor._get_param_value(item, "Цена")

        assert result == "200 000"

    def test_get_param_value_not_found(self, extractor):
        """Test returns empty string when param not found."""
        html = '<div class="item"></div>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".item")
        result = extractor._get_param_value(item, "Цена")

        assert result == ""

    def test_get_listing_data_no_title(self, extractor):
        """Test returns None when no title element."""
        html = '<div class="listtop-item"><div>No title here</div></div>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one(".listtop-item")
        result = extractor._get_listing_data(item)

        assert result is None

    def test_get_details_url_adds_slash_to_href(self, extractor):
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
        result = extractor._get_listing_data(item)

        assert result["details_url"] == "/obiava/123"


# =============================================================================
# End-to-End Integration Tests
# =============================================================================


class TestAloBgEndToEnd:
    """Test the full extraction and transformation pipeline."""

    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_full_pipeline(self, extractor, transformer):
        """Test extracting and transforming a listing."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")

        # Extract
        raw_listings = list(extractor.extract_listings(soup))
        assert len(raw_listings) == 1

        # Transform
        result = transformer.transform(raw_listings[0])

        # Verify transformed data
        assert result.site == "alobg"
        assert result.price == 150000.0
        assert result.original_currency == "EUR"
        # Note: Transformer parses "X, Y" as city=X, neighborhood=Y
        assert result.city == "Лозенец"
        assert result.neighborhood == "София"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.area == 65.0
        # Plain numbers are now recognized as floors
        assert result.floor == "3"
        assert result.ref_no == "12345"
        assert result.num_photos == 2
        assert result.fingerprint_hash != ""

    def test_full_pipeline_multiple(self, extractor, transformer):
        """Test extracting and transforming multiple listings."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

        # Extract
        raw_listings = list(extractor.extract_listings(soup))
        assert len(raw_listings) == 2

        # Transform all
        results = transformer.transform_batch(raw_listings)
        assert len(results) == 2

        # Verify first listing (sale)
        assert results[0].offer_type == "продава"
        # Note: Transformer parses "X, Y" as city=X, neighborhood=Y
        assert results[0].city == "Лозенец"

        # Verify second listing (rent)
        assert results[1].offer_type == "наем"
        assert results[1].city == "Център"


# =============================================================================
# Extract Total Floors Tests
# =============================================================================


class TestExtractTotalFloors:
    """Test the extract_total_floors method."""

    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    def test_extract_total_floors_etajnost(self, extractor):
        assert extractor.extract_total_floors("Етажност: 8") == "8"

    def test_extract_total_floors_etajnost_na_sgradata(self, extractor):
        assert extractor.extract_total_floors("Етажност на сградата: 12") == "12"

    def test_extract_total_floors_ot_pattern_etaja(self, extractor):
        assert extractor.extract_total_floors("3-ти от 8 етажа") == "8"

    def test_extract_total_floors_ot_pattern_et(self, extractor):
        assert extractor.extract_total_floors("5-ти от 10 ет.") == "10"

    def test_extract_total_floors_etajna_sgrda(self, extractor):
        assert extractor.extract_total_floors("Сградата е 6-етажна с асансьор") == "6"

    def test_extract_total_floors_empty(self, extractor):
        assert extractor.extract_total_floors("") == ""

    def test_extract_total_floors_no_match(self, extractor):
        assert extractor.extract_total_floors("Апартамент в новострой") == ""

    def test_extract_total_floors_none(self, extractor):
        assert extractor.extract_total_floors(None) == ""


# =============================================================================
# New Fields Extraction Tests
# =============================================================================


class TestAloBgExtractorNewFields:
    """Test extraction of raw_link_description and total_floors_text."""

    @pytest.fixture
    def extractor(self):
        return AloBgExtractor()

    def test_extract_raw_link_description_from_link_title(self, extractor):
        """Test extracting raw_link_description from link title attribute."""
        html = """
        <div class="listtop-item">
            <a href="/obiava/12345" title="Продава двустаен апартамент в Лозенец">
                <h3 class="listtop-item-title">Продава двустаен апартамент</h3>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == "Продава двустаен апартамент в Лозенец"

    def test_extract_raw_link_description_from_h3_title(self, extractor):
        """Test extracting raw_link_description from h3 title attribute as fallback."""
        html = """
        <div class="listtop-item">
            <a href="/obiava/12345">
                <h3 class="listtop-item-title" title="Описание на имота">Продава двустаен</h3>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == "Описание на имота"

    def test_extract_raw_link_description_empty(self, extractor):
        """Test that raw_link_description is empty when no title attribute exists."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))
        # SAMPLE_LISTING_HTML doesn't have title attribute on link or h3
        assert listings[0].raw_link_description == ""

    def test_extract_total_floors_from_description(self, extractor):
        """Test extracting total_floors_text from description."""
        html = """
        <div class="listtop-item">
            <a href="/obiava/12345">
                <h3 class="listtop-item-title">Продава двустаен апартамент</h3>
            </a>
            <p class="listtop-desc">Апартамент на 3-ти от 8 етажа в нова сграда.</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == "8"

    def test_extract_total_floors_from_param(self, extractor):
        """Test extracting total_floors_text from Етажност parameter."""
        html = """
        <div class="listtop-item">
            <a href="/obiava/12345">
                <h3 class="listtop-item-title">Продава двустаен апартамент</h3>
            </a>
            <div class="ads-params-row">
                <div class="ads-param-title">Етажност:</div>
                <div class="ads-params-cell"><span class="ads-params-single">10</span></div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == "10"

    def test_extract_total_floors_empty(self, extractor):
        """Test that total_floors_text is empty when not available."""
        soup = BeautifulSoup(SAMPLE_LISTING_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))
        # SAMPLE_LISTING_HTML description doesn't have total floors info
        assert listings[0].total_floors_text == ""


# =============================================================================
# Transformer Integration Tests for New Fields
# =============================================================================


class TestAloBgTransformTotalFloors:
    """Test that total_floors is correctly passed through transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_with_total_floors(self, transformer):
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
            floor_text="3",
            total_floors_text="8",
            description="Описание",
            agency_name="Агенция Имоти",
        )
        result = transformer.transform(raw)
        assert result.total_floors == "8"

    def test_transform_with_empty_total_floors(self, transformer):
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
            floor_text="3",
            total_floors_text="",
            description="Описание",
            agency_name="Агенция Имоти",
        )
        result = transformer.transform(raw)
        assert result.total_floors == ""

    def test_transform_with_none_total_floors(self, transformer):
        raw = RawListing(
            site="alobg",
            title="Продава двустаен апартамент",
            details_url="https://www.alo.bg/obiava/12345",
            location_text="Лозенец, София",
            price_text="150 000 EUR",
            area_text="65 кв.м.",
            floor_text="3",
            total_floors_text=None,
            description="Описание",
            agency_name="Агенция Имоти",
        )
        result = transformer.transform(raw)
        assert result.total_floors is None
