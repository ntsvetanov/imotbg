import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.bulgarianproperties import BulgarianPropertiesExtractor

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


class TestBulgarianPropertiesExtractorConfig:
    def test_config_values(self):
        extractor = BulgarianPropertiesExtractor()
        assert extractor.config.name == "bulgarianproperties"
        assert extractor.config.base_url == "https://www.bulgarianproperties.bg"
        assert extractor.config.encoding == "windows-1251"
        assert extractor.config.rate_limit_seconds == 1.5


class TestBulgarianPropertiesExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return BulgarianPropertiesExtractor()

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
        assert listings[0].title == "Тристаен апартамент в София"

    def test_extract_listing_location(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == "гр. София, Лозенец"

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert (
            listings[0].details_url == "https://www.bulgarianproperties.bg/imoti/apartament-sofia-lozenets/12345.html"
        )

    def test_extract_listing_area_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "85" in listings[0].area_text

    def test_extract_listing_description(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "Просторен" in listings[0].description

    def test_extract_listing_ref_no_from_element(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "BP12345" in listings[0].ref_no

    def test_extract_listing_ref_no_from_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        # Second listing has no ref element, should extract from URL
        assert listings[1].ref_no == "67890"

    def test_extract_listing_agency_name(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == "Иван Иванов"

    def test_extract_listing_agency_name_default(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        # Second listing has no broker, should use default
        assert listings[1].agency_name == "Bulgarian Properties"

    def test_extract_listing_new_fields(self, extractor, soup):
        """Test that new fields are present in extracted listings."""
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos is not None
        assert listings[0].total_offers is not None
        assert listings[0].scraped_at is not None

    def test_extract_listing_new_price(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "500" in listings[1].price_text

    def test_extract_listing_returns_raw_listing_objects(self, extractor, soup):
        """Verify that extract_listings yields RawListing objects."""
        listings = list(extractor.extract_listings(soup))
        assert all(isinstance(listing, RawListing) for listing in listings)

    def test_extract_listing_site_field(self, extractor, soup):
        """Verify site field is populated correctly."""
        listings = list(extractor.extract_listings(soup))
        assert all(listing.site == "bulgarianproperties" for listing in listings)


class TestTransformer:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="185 000 €",
            title="Тристаен апартамент в София",
            location_text="гр. София, Лозенец",
            area_text="85 кв.м.",
            description="Nice apartment",
            details_url="https://www.bulgarianproperties.bg/imoti-tristayni-apartamenti/imot-12345-tristaen-apartament-v-sofiya.html",
            ref_no="BP12345",
            agency_name="Agent Name",
            search_url="https://www.bulgarianproperties.bg/Search/index.php?stown=4732",
        )
        result = transformer.transform(raw)

        assert result.site == "bulgarianproperties"
        assert result.price == 185000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "тристаен"
        assert result.area == 85.0
        assert result.agency == "Agent Name"
        assert result.search_url == "https://www.bulgarianproperties.bg/Search/index.php?stown=4732"
        assert (
            result.details_url
            == "https://www.bulgarianproperties.bg/imoti-tristayni-apartamenti/imot-12345-tristaen-apartament-v-sofiya.html"
        )

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="250 000 лв.",
            title="Двустаен апартамент",
            location_text="гр. Пловдив, Център",
            area_text="65 m2",
            description="",
            details_url="/imoti/123.html",
            ref_no="123",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)

        # Price should be converted from BGN to EUR
        assert result.price == round(250000.0 / 1.9558, 2)
        assert result.original_currency == "BGN"

    def test_transform_listing_rent(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="500 €",
            title="Двустаен апартамент под наем",
            location_text="гр. София, Център",
            area_text="65 кв.м.",
            description="",
            details_url="/imoti-dvustayni-apartamenti/imot-555-dvustaen-apartament-pod-naem-v-sofiya.html",
            ref_no="555",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"
        assert result.agency == "Bulgarian Properties"

    def test_transform_missing_location(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="100 €",
            title="Test",
            location_text="",
            area_text="",
            description="",
            details_url="/imot.html",
            ref_no="",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)
        assert result.city == ""
        assert result.neighborhood == ""

    def test_transform_price_per_m2_calculated(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="100 000 €",
            title="Апартамент",
            location_text="гр. София",
            area_text="50 кв.м.",
            description="",
            details_url="/imot.html",
            ref_no="",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)
        assert result.price_per_m2 == 2000.0


class TestTransformerLocationParsing:
    """Test location parsing via the Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_city_with_prefix_gr(self, transformer):
        raw = RawListing(site="test", location_text="гр. София, Лозенец")
        result = transformer.transform(raw)
        assert result.city == "София"

    def test_city_with_prefix_grad(self, transformer):
        raw = RawListing(site="test", location_text="град София, Център")
        result = transformer.transform(raw)
        assert result.city == "София"

    def test_neighborhood_standard(self, transformer):
        raw = RawListing(site="test", location_text="гр. София, Лозенец")
        result = transformer.transform(raw)
        assert result.neighborhood == "Лозенец"

    def test_neighborhood_no_neighborhood(self, transformer):
        raw = RawListing(site="test", location_text="гр. София")
        result = transformer.transform(raw)
        assert result.neighborhood == ""

    def test_empty_location(self, transformer):
        raw = RawListing(site="test", location_text="")
        result = transformer.transform(raw)
        assert result.city == ""
        assert result.neighborhood == ""


class TestTransformerOfferType:
    """Test offer type extraction via the Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_pod_naem_in_url(self, transformer):
        raw = RawListing(
            site="test",
            details_url="/imoti-dvustayni-apartamenti/imot-89147-dvustaen-apartament-pod-naem-v-sofiya.html",
        )
        result = transformer.transform(raw)
        assert result.offer_type == "наем"

    def test_naem_in_url(self, transformer):
        raw = RawListing(site="test", details_url="/imoti/imot-123-naem-sofia.html")
        result = transformer.transform(raw)
        assert result.offer_type == "наем"

    def test_prodava_in_url(self, transformer):
        raw = RawListing(site="test", details_url="/imoti/imot-123-prodava-sofia.html")
        result = transformer.transform(raw)
        assert result.offer_type == "продава"

    def test_prodazhba_in_url(self, transformer):
        raw = RawListing(site="test", details_url="/prodazhba/imot-123.html")
        result = transformer.transform(raw)
        assert result.offer_type == "продава"

    def test_no_offer_type_match(self, transformer):
        raw = RawListing(site="test", details_url="/imoti/imot-123.html")
        result = transformer.transform(raw)
        assert result.offer_type == ""

    def test_empty_url(self, transformer):
        raw = RawListing(site="test", details_url="")
        result = transformer.transform(raw)
        assert result.offer_type == ""


class TestTransformerPropertyType:
    """Test property type extraction via the Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_ednostaen_in_url(self, transformer):
        raw = RawListing(site="test", details_url="/imoti-ednostayni-apartamenti/imot-123.html")
        result = transformer.transform(raw)
        assert result.property_type == "едностаен"

    def test_dvustaen_in_url(self, transformer):
        raw = RawListing(
            site="test",
            details_url="/imoti-dvustayni-apartamenti/imot-89147-dvustaen-apartament-v-sofiya.html",
        )
        result = transformer.transform(raw)
        assert result.property_type == "двустаен"

    def test_tristaen_in_url(self, transformer):
        raw = RawListing(site="test", details_url="/imoti-tristayni-apartamenti/imot-123.html")
        result = transformer.transform(raw)
        assert result.property_type == "тристаен"

    def test_chetiristaen_in_url(self, transformer):
        raw = RawListing(site="test", details_url="/imoti-chetiristayni-apartamenti/imot-123.html")
        result = transformer.transform(raw)
        assert result.property_type == "четиристаен"

    def test_mezonet_in_url(self, transformer):
        raw = RawListing(
            site="test",
            details_url="/imoti-mezoneti/imot-89171-mezonet-pod-naem-v-sofiya.html",
        )
        result = transformer.transform(raw)
        assert result.property_type == "мезонет"

    def test_no_property_type_match(self, transformer):
        raw = RawListing(site="test", details_url="/imoti/imot-123.html")
        result = transformer.transform(raw)
        assert result.property_type == ""

    def test_empty_url(self, transformer):
        raw = RawListing(site="test", details_url="")
        result = transformer.transform(raw)
        assert result.property_type == ""


class TestBulgarianPropertiesExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return BulgarianPropertiesExtractor()

    def test_get_total_pages(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        total = extractor.get_total_pages(soup)
        assert total == 3

    def test_get_total_pages_no_pagination(self, extractor):
        html = """
        <html><body>
        <div class="component-property-item">
            <a class="title" href="/imot.html">Test</a>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        total = extractor.get_total_pages(soup)
        # Returns max_pages when no pagination found
        assert total == extractor.config.max_pages

    def test_get_next_page_url_page_2(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert next_url == "https://www.bulgarianproperties.bg/sofia/apartments?page=2"

    def test_get_next_page_url_existing_query(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments?type=flat"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert next_url == "https://www.bulgarianproperties.bg/sofia/apartments?type=flat&page=2"

    def test_get_next_page_url_replace_page(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments?page=2"
        next_url = extractor.get_next_page_url(soup, url, 3)
        assert next_url == "https://www.bulgarianproperties.bg/sofia/apartments?page=3"

    def test_get_next_page_url_beyond_total(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments"
        next_url = extractor.get_next_page_url(soup, url, 4)
        assert next_url is None

    def test_get_next_page_url_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.bulgarianproperties.bg/sofia/apartments"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert next_url is None


class TestBulgarianPropertiesExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return BulgarianPropertiesExtractor()

    def test_extract_listings_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, extractor):
        html = """
        <div class="component-property-item">
            <span class="regular-price">100 €</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].title == ""

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == ""

    def test_extract_listing_missing_location(self, extractor):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
            <span class="regular-price">100 €</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == ""

    def test_extract_listing_missing_size(self, extractor):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].area_text == ""

    def test_extract_listing_missing_description(self, extractor):
        html = """
        <div class="component-property-item">
            <a class="title" href="/imot.html">Апартамент</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].description == ""

    def test_extract_listing_alternative_link_selector(self, extractor):
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
        listings = list(extractor.extract_listings(soup))
        assert listings[0].details_url == "https://www.bulgarianproperties.bg/imoti/alt-123.html"


class TestTransformerEdgeCases:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_details_url_already_absolute(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="100 €",
            title="Test",
            location_text="",
            area_text="",
            description="",
            details_url="https://www.bulgarianproperties.bg/absolute/path.html",
            ref_no="",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)
        # Should preserve the URL as-is
        assert result.details_url == "https://www.bulgarianproperties.bg/absolute/path.html"


class TestBulgarianPropertiesExtractTotalFloors:
    """Test the _get_total_floors method."""

    @pytest.fixture
    def extractor(self):
        return BulgarianPropertiesExtractor()

    def test_extract_total_floors_simple(self, extractor):
        assert extractor._get_total_floors("Етажност: 8") == "8"

    def test_extract_total_floors_with_space(self, extractor):
        assert extractor._get_total_floors("Етажност:  10") == "10"

    def test_extract_total_floors_full_pattern(self, extractor):
        assert extractor._get_total_floors("Етажност на сградата: 6") == "6"

    def test_extract_total_floors_from_complex_text(self, extractor):
        assert extractor._get_total_floors("Площ: 85 кв.м.Етаж: 5Етажност: 8") == "8"

    def test_extract_total_floors_alternative_pattern(self, extractor):
        assert extractor._get_total_floors("3-ти от 8 етажа") == "8"

    def test_extract_total_floors_empty(self, extractor):
        assert extractor._get_total_floors("") == ""

    def test_extract_total_floors_none(self, extractor):
        assert extractor._get_total_floors(None) == ""

    def test_extract_total_floors_no_match(self, extractor):
        assert extractor._get_total_floors("Площ: 85 кв.м.Етаж: 5") == ""


class TestBulgarianPropertiesExtractorNewFields:
    """Test extraction of new fields: total_floors_text, raw_link_description."""

    @pytest.fixture
    def extractor(self):
        return BulgarianPropertiesExtractor()

    def test_extract_raw_link_description(self, extractor):
        html = """
        <html><body>
        <div class="component-property-item">
            <a class="title" href="/imoti/apartament-sofia/12345.html" title="Тристаен апартамент в София - красива гледка">
                Тристаен апартамент в София
            </a>
            <span class="regular-price">185 000 €</span>
            <span class="location">гр. София, Лозенец</span>
            <span class="size">85 кв.м.</span>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].raw_link_description == "Тристаен апартамент в София - красива гледка"

    def test_extract_raw_link_description_empty(self, extractor):
        html = """
        <html><body>
        <div class="component-property-item">
            <a class="title" href="/imoti/apartament-sofia/12345.html">
                Тристаен апартамент в София
            </a>
            <span class="regular-price">185 000 €</span>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].raw_link_description == ""

    def test_extract_total_floors_text(self, extractor):
        html = """
        <html><body>
        <div class="component-property-item">
            <a class="title" href="/imoti/apartament-sofia/12345.html">Апартамент</a>
            <span class="regular-price">185 000 €</span>
            <span class="size">Площ: 85 кв.м.Етаж: 5Етажност: 8</span>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].total_floors_text == "8"
        assert listings[0].floor_text == "5"

    def test_extract_total_floors_text_empty(self, extractor):
        html = """
        <html><body>
        <div class="component-property-item">
            <a class="title" href="/imoti/apartament-sofia/12345.html">Апартамент</a>
            <span class="regular-price">185 000 €</span>
            <span class="size">85 кв.м.</span>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].total_floors_text == ""


class TestBulgarianPropertiesTransformTotalFloors:
    """Test that total_floors_text is correctly passed through transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_with_total_floors(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="185 000 €",
            title="Тристаен апартамент в София",
            location_text="гр. София, Лозенец",
            area_text="85 кв.м.",
            floor_text="5",
            total_floors_text="8",
            description="",
            details_url="/imoti/12345.html",
            ref_no="12345",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)

        assert result.total_floors == "8"
        assert result.floor == "5"

    def test_transform_with_empty_total_floors(self, transformer):
        raw = RawListing(
            site="bulgarianproperties",
            price_text="185 000 €",
            title="Тристаен апартамент",
            location_text="гр. София",
            area_text="85 кв.м.",
            floor_text="5",
            total_floors_text="",
            description="",
            details_url="/imoti/12345.html",
            ref_no="12345",
            agency_name="Bulgarian Properties",
        )
        result = transformer.transform(raw)

        assert result.total_floors == ""
        assert result.floor == "5"
