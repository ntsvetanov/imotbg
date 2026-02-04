import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.bazarbg import BazarBgExtractor

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


class TestBazarBgExtractorConfig:
    def test_config_values(self):
        extractor = BazarBgExtractor()
        assert extractor.config.name == "bazarbg"
        assert extractor.config.base_url == "https://bazar.bg"
        assert extractor.config.encoding == "utf-8"
        assert extractor.config.rate_limit_seconds == 1.5


class TestBazarBgExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return BazarBgExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_title(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].title == "Продава 2-стаен апартамент"

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].details_url == "https://bazar.bg/ad/12345"

    def test_extract_listing_ref_no(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].ref_no == "12345"

    def test_extract_listing_price_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == "179 000 EUR"

    def test_extract_listing_location_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == "гр. София, Лозенец"

    def test_extract_listing_returns_raw_listing(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert isinstance(listings[0], RawListing)
        assert listings[0].site == "bazarbg"

    def test_extract_listing_new_fields(self, extractor, soup):
        """Test that new fields are present in extracted listings."""
        listings = list(extractor.extract_listings(soup))
        assert listings[0].area_text is not None or listings[0].area_text == ""
        assert listings[0].floor_text is not None or listings[0].floor_text == ""
        assert listings[0].num_photos is not None
        assert listings[0].total_offers is not None

    def test_extract_listings_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listings_missing_link(self, extractor):
        html = """
        <div class="listItemContainer">
            <span class="other">No link here</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="location">гр. София</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].price_text == ""

    def test_extract_listing_missing_location(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].location_text == ""

    def test_extract_listing_missing_data_id(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].ref_no == ""


class TestTransformerWithBazarBgData:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing_eur(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава 2-стаен апартамент",
            price_text="179 000 EUR",
            location_text="гр. София, Лозенец",
            details_url="https://bazar.bg/ad/12345",
            ref_no="12345",
        )
        result = transformer.transform(raw)

        assert result.site == "bazarbg"
        assert result.price == 179000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.details_url == "https://bazar.bg/ad/12345"
        assert result.ref_no == "12345"

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава 3-стаен апартамент",
            price_text="250 000 лв.",
            location_text="гр. Пловдив, Център",
            details_url="https://bazar.bg/ad/67890",
            ref_no="67890",
        )
        result = transformer.transform(raw)

        assert result.site == "bazarbg"
        # BGN is converted to EUR
        assert result.price == pytest.approx(127809.11, rel=1e-2)
        assert result.original_currency == "BGN"
        assert result.city == "Пловдив"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"

    def test_transform_listing_missing_price(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава апартамент",
            price_text="",
            location_text="гр. София",
            details_url="https://bazar.bg/ad/123",
            ref_no="123",
        )
        result = transformer.transform(raw)

        assert result.price is None
        assert result.original_currency == ""

    def test_transform_listing_missing_location(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава апартамент",
            price_text="100 EUR",
            location_text="",
            details_url="https://bazar.bg/ad/123",
            ref_no="123",
        )
        result = transformer.transform(raw)

        assert result.city == ""
        assert result.neighborhood == ""

    def test_transform_listing_naem(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Под наем 2-стаен",
            price_text="1 000 лв.",
            location_text="гр. София, Витоша",
            details_url="https://bazar.bg/ad/999",
            ref_no="999",
        )
        result = transformer.transform(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"

    def test_transform_listing_village_location(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава къща",
            price_text="50 000 EUR",
            location_text="с. Равда",
            details_url="https://bazar.bg/ad/123",
            ref_no="123",
        )
        result = transformer.transform(raw)

        assert result.city == "Равда"
        assert result.neighborhood == ""

    def test_transform_listing_garage_property_type(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава гараж",
            price_text="10 000 EUR",
            location_text="гр. София",
            details_url="https://bazar.bg/ad/123",
            ref_no="123",
        )
        result = transformer.transform(raw)

        assert result.property_type == "гараж"
        assert result.offer_type == "продава"

    def test_transform_listing_complex_location(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава 2-стаен",
            price_text="100 000 EUR",
            location_text="гр. София, Витоша, ж.к. Манастирски ливади",
            details_url="https://bazar.bg/ad/123",
            ref_no="123",
        )
        result = transformer.transform(raw)

        assert result.city == "София"
        # Neighborhood is normalized - first matching neighborhood is used
        assert result.neighborhood in ["Витоша", "Манастирски ливади"]


class TestBazarBgExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return BazarBgExtractor()

    def test_get_total_pages(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        assert extractor.get_total_pages(soup) == 10

    def test_get_total_pages_no_pagination(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert extractor.get_total_pages(soup) == 1

    def test_get_total_pages_no_page_links(self, extractor):
        html = """
        <html><body>
        <div class="paging">
            <a class="btn current">1</a>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert extractor.get_total_pages(soup) == 1

    def test_get_total_pages_non_numeric_last_page(self, extractor):
        html = """
        <html><body>
        <div class="paging">
            <a class="btn current">1</a>
            <a class="btn not-current">Next</a>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert extractor.get_total_pages(soup) == 1

    def test_get_next_page_url_basic(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search?type=apartment"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://bazar.bg/search?type=apartment&page=2"

    def test_get_next_page_url_no_query(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://bazar.bg/search?page=2"

    def test_get_next_page_url_existing_page(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search?type=apartment&page=2"
        next_url = extractor.get_next_page_url(soup, url, 3)

        assert next_url == "https://bazar.bg/search?type=apartment&page=3"

    def test_get_next_page_url_exceeds_total(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search?type=apartment"
        next_url = extractor.get_next_page_url(soup, url, 11)

        assert next_url is None

    def test_get_next_page_url_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://bazar.bg/search"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url is None

    def test_get_next_page_url_page_equals_total(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search"
        next_url = extractor.get_next_page_url(soup, url, 10)

        assert next_url == "https://bazar.bg/search?page=10"

    def test_get_next_page_url_page_one(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://bazar.bg/search"
        next_url = extractor.get_next_page_url(soup, url, 1)

        assert next_url == "https://bazar.bg/search?page=1"


class TestBazarBgExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return BazarBgExtractor()

    def test_extract_listing_special_characters_in_title(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="&quot;Луксозен&quot; апартамент &amp; СПА" data-id="123">
                <span class="price">500 000 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert '"Луксозен" апартамент & СПА' in listings[0].title

    def test_extract_listing_whitespace_in_price(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" title="Test" data-id="123">
                <span class="price">  179 000   EUR  </span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == "179 000   EUR"

    def test_extract_listing_empty_href(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="" title="Test" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].details_url == ""

    def test_extract_listing_missing_title_attribute(self, extractor):
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/123" data-id="123">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].title == ""


# =============================================================================
# Extract Total Floors Tests
# =============================================================================


class TestExtractTotalFloors:
    """Test the extract_total_floors method."""

    @pytest.fixture
    def extractor(self):
        return BazarBgExtractor()

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


class TestBazarBgExtractorNewFields:
    """Test extraction of raw_link_description and total_floors_text."""

    @pytest.fixture
    def extractor(self):
        return BazarBgExtractor()

    def test_extract_raw_link_description(self, extractor):
        """Test extracting raw_link_description from link title attribute."""
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/12345" title="Продава 3-СТАЕН, гр. София, Лозенец" data-id="12345">
                <span class="price">319 000 €</span>
                <span class="location">гр. София, Лозенец</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == "Продава 3-СТАЕН, гр. София, Лозенец"

    def test_extract_raw_link_description_empty(self, extractor):
        """Test that raw_link_description is empty when no title attribute exists."""
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/12345" data-id="12345">
                <span class="price">100 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == ""

    def test_extract_total_floors_from_title(self, extractor):
        """Test extracting total_floors_text from title."""
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/12345" title="Продава 2-стаен, 3-ти от 8 етажа" data-id="12345">
                <span class="price">150 000 EUR</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == "8"

    def test_extract_total_floors_empty(self, extractor):
        """Test that total_floors_text is empty when not available."""
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        listings = list(extractor.extract_listings(soup))
        # SAMPLE_PAGE_HTML titles don't have total floors info
        assert listings[0].total_floors_text == ""

    def test_extract_price_with_nested_currency_span(self, extractor):
        """Test extracting price when currency is in a nested span element."""
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/53205356" title="Продава 3-СТАЕН, гр. София, Лозенец" data-id="53205356">
                <span class="price">319 000 <span class="currency">€</span></span>
                <span class="price">623 909,77 <span class="currency">лв</span></span>
                <span class="location">гр. София, Лозенец</span>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        # First price span is selected (EUR price)
        assert "319 000" in listings[0].price_text
        assert "€" in listings[0].price_text

    def test_extract_price_multiple_price_spans_takes_first(self, extractor):
        """Test that when multiple price spans exist, the first one (EUR) is used."""
        html = """
        <div class="listItemContainer">
            <a class="listItemLink" href="/ad/12345" title="Test" data-id="12345">
                <div class="title">
                    <span class="price">150 000 <span class="currency">€</span></span>
                    <span class="price">293 370,00 <span class="currency">лв</span></span>
                </div>
            </a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        # Should extract first price (EUR)
        assert "150 000" in listings[0].price_text
        assert "€" in listings[0].price_text


# =============================================================================
# Transformer Integration Tests for New Fields
# =============================================================================


class TestBazarBgTransformTotalFloors:
    """Test that total_floors is correctly passed through transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_with_total_floors(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава 2-стаен апартамент",
            price_text="179 000 EUR",
            location_text="гр. София, Лозенец",
            details_url="https://bazar.bg/ad/12345",
            ref_no="12345",
            total_floors_text="8",
        )
        result = transformer.transform(raw)
        assert result.total_floors == "8"

    def test_transform_with_empty_total_floors(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава 2-стаен апартамент",
            price_text="179 000 EUR",
            location_text="гр. София, Лозенец",
            details_url="https://bazar.bg/ad/12345",
            ref_no="12345",
            total_floors_text="",
        )
        result = transformer.transform(raw)
        assert result.total_floors == ""

    def test_transform_with_none_total_floors(self, transformer):
        raw = RawListing(
            site="bazarbg",
            title="Продава 2-стаен апартамент",
            price_text="179 000 EUR",
            location_text="гр. София, Лозенец",
            details_url="https://bazar.bg/ad/12345",
            ref_no="12345",
            total_floors_text=None,
        )
        result = transformer.transform(raw)
        assert result.total_floors is None
