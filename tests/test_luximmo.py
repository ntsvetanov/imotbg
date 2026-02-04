import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.luximmo import LuximmoExtractor

SAMPLE_LISTING_HTML = """
<div class="card mb-4">
    <a class="card-url" href="https://www.luximmo.bg/za-prodajba/luksozen-imot-43445-tsentyr-sofia.html">Link</a>
    <h4 class="card-title">Тристаен апартамент за продажба</h4>
    <div class="card-price">185 000 €<br/>361 825 лв.</div>
    <div class="card-loc-dis">
        <span class="text-dark">гр. София / кв. Център</span>
    </div>
    <div class="card-dis">Площ: 95.5 м Етаж: 3</div>
    <div class="carousel-item"><img src="photo1.jpg"/></div>
    <div class="carousel-item"><img src="photo2.jpg"/></div>
    <div class="carousel-item"><img src="photo3.jpg"/></div>
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
    <div class="card-img"><img src="photo1.jpg"/></div>
</div>
<ul class="pagination">
    <li><a class="page-link" href="index.html">1</a></li>
    <li><a class="page-link" href="index1.html">2</a></li>
    <li><a class="page-link" href="index2.html">3</a></li>
</ul>
</body>
</html>
"""


class TestTransformerExtractCity:
    """Test Transformer city extraction via _parse_location."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_with_prefix_gr(self, transformer):
        city, _ = transformer._parse_location("гр. София / кв. Лозенец")
        assert city == "София"

    def test_with_prefix_grad(self, transformer):
        city, _ = transformer._parse_location("град София / Център")
        assert city == "София"

    def test_without_prefix(self, transformer):
        city, _ = transformer._parse_location("София / Лозенец")
        assert city == "София"

    def test_empty(self, transformer):
        city, _ = transformer._parse_location("")
        assert city == ""

    def test_none(self, transformer):
        city, _ = transformer._parse_location(None)
        assert city == ""


class TestTransformerExtractNeighborhood:
    """Test Transformer neighborhood extraction via _parse_location."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_with_kv_prefix(self, transformer):
        # _parse_location returns raw neighborhood; normalization happens in transform()
        _, neighborhood = transformer._parse_location("гр. София / кв. Лозенец")
        assert neighborhood == "Лозенец"

    def test_without_prefix(self, transformer):
        _, neighborhood = transformer._parse_location("София / Център")
        assert neighborhood == "Център"

    def test_no_neighborhood(self, transformer):
        _, neighborhood = transformer._parse_location("гр. София")
        assert neighborhood == ""

    def test_empty(self, transformer):
        _, neighborhood = transformer._parse_location("")
        assert neighborhood == ""


class TestTransformerExtractArea:
    """Test Transformer area extraction."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_standard_format(self, transformer):
        assert transformer._extract_area("95.5 м²") == 95.5

    def test_with_comma(self, transformer):
        assert transformer._extract_area("207,43 м²") == 207.43

    def test_integer(self, transformer):
        assert transformer._extract_area("100 м²") == 100

    def test_no_match(self, transformer):
        assert transformer._extract_area("No area here") is None

    def test_empty(self, transformer):
        assert transformer._extract_area("") is None


class TestLuximmoExtractorConfig:
    def test_config_values(self):
        extractor = LuximmoExtractor()
        assert extractor.config.name == "luximmo"
        assert extractor.config.base_url == "https://www.luximmo.bg"
        assert extractor.config.encoding == "windows-1251"
        assert extractor.config.rate_limit_seconds == 1.5


class TestLuximmoExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return LuximmoExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "185000" in listings[0].price_text or "185 000" in listings[0].price_text

    def test_extract_listing_title(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "Тристаен апартамент" in listings[0].title

    def test_extract_listing_location(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "София" in listings[0].location_text
        assert "Център" in listings[0].location_text

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "43445" in listings[0].details_url
        assert "za-prodajba" in listings[0].details_url

    def test_extract_listing_area_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "95.5" in listings[0].area_text

    def test_extract_listing_floor(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == "3"

    def test_extract_listing_ref_no(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].ref_no == "43445"

    def test_extract_listing_agency_name(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == "Luximmo"

    def test_extract_listing_num_photos(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 3  # 3 carousel items
        assert listings[1].num_photos == 1  # 1 card-img

    def test_extract_listing_returns_raw_listing(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert isinstance(listings[0], RawListing)


class TestTransformerTransformListing:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="185000 €",
            title="Тристаен апартамент за продажба",
            location_text="гр. София / кв. Център",
            area_text="95.5 м",
            floor_text="3",
            description="",
            details_url="https://www.luximmo.bg/za-prodajba/imot-43445.html",
            ref_no="43445",
            agency_name="Luximmo",
        )
        result = transformer.transform(raw)

        assert result.site == "luximmo"
        assert result.price == 185000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"
        assert result.offer_type == "продава"
        assert result.area == 95.5
        assert result.floor == "3"
        assert result.ref_no == "43445"

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="250 000 лв.",
            title="Двустаен апартамент",
            location_text="гр. Пловдив / кв. Център",
            area_text="65 м",
            floor_text="",
            description="",
            details_url="https://www.luximmo.bg/imot-123.html",
            ref_no="123",
            agency_name="Luximmo",
        )
        result = transformer.transform(raw)

        # Price should be converted from BGN to EUR
        expected_eur = round(250000.0 / 1.9558, 2)
        assert result.price == expected_eur
        assert result.original_currency == "BGN"

    def test_transform_listing_rent(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="800 €",
            title="Двустаен апартамент под наем",
            location_text="гр. София / кв. Лозенец",
            area_text="65 м",
            floor_text="5",
            description="",
            details_url="https://www.luximmo.bg/pod-naem/imot-555.html",
            ref_no="555",
            agency_name="Luximmo",
        )
        result = transformer.transform(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"

    def test_transform_listing_with_new_fields(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="185000 €",
            title="Тристаен апартамент за продажба",
            location_text="гр. София / кв. Център",
            area_text="95.5 м",
            floor_text="3",
            description="",
            details_url="https://www.luximmo.bg/za-prodajba/imot-43445.html",
            ref_no="43445",
            agency_name="Luximmo",
            num_photos=5,
            total_offers=100,
        )
        result = transformer.transform(raw)

        assert result.num_photos == 5
        assert result.total_offers == 100
        # price_per_m2 is now calculated by transformer
        expected_price_per_m2 = round(185000.0 / 95.5, 2)
        assert result.price_per_m2 == expected_price_per_m2

    def test_transform_listing_with_search_url(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="185000 €",
            title="Тристаен апартамент за продажба",
            location_text="гр. София / кв. Център",
            area_text="95.5 м",
            floor_text="3",
            description="",
            details_url="https://www.luximmo.bg/za-prodajba/imot-43445.html",
            ref_no="43445",
            agency_name="Luximmo",
            num_photos=5,
            total_offers=100,
            search_url="https://www.luximmo.bg/sofia/apartments/",
        )
        result = transformer.transform(raw)

        assert result.search_url == "https://www.luximmo.bg/sofia/apartments/"


class TestLuximmoExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return LuximmoExtractor()

    def test_get_total_pages(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        total = extractor.get_total_pages(soup)
        assert total == 3

    def test_get_total_pages_no_pagination(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        total = extractor.get_total_pages(soup)
        assert total == 1

    def test_get_next_page_url_page_1(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = extractor.get_next_page_url(soup, url, 1)
        assert next_url == "https://www.luximmo.bg/sofia/apartments/index.html"

    def test_get_next_page_url_page_2(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert next_url == "https://www.luximmo.bg/sofia/apartments/index1.html"

    def test_get_next_page_url_page_3(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index1.html"
        next_url = extractor.get_next_page_url(soup, url, 3)
        assert next_url == "https://www.luximmo.bg/sofia/apartments/index2.html"

    def test_get_next_page_url_beyond_total(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = extractor.get_next_page_url(soup, url, 4)
        assert next_url is None

    def test_get_next_page_url_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/index.html"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert next_url is None

    def test_get_next_page_url_no_index_in_url(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.luximmo.bg/sofia/apartments/"
        next_url = extractor.get_next_page_url(soup, url, 2)
        assert "index1.html" in next_url


class TestLuximmoExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return LuximmoExtractor()

    def test_extract_listings_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listings_card_without_url(self, extractor):
        html = """
        <div class="card mb-4">
            <h4 class="card-title">No URL Card</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <div class="card-price">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].title == ""

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == ""

    def test_extract_listing_missing_location(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-price">100 €</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == ""

    def test_extract_listing_missing_area(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-dis">Some other info</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].area_text == ""

    def test_extract_listing_missing_floor(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-dis">Площ: 50 м</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == ""

    def test_transform_missing_location(self):
        transformer = Transformer()
        raw = RawListing(
            site="luximmo",
            price_text="100 €",
            title="Test",
            location_text="",
            area_text="",
            floor_text="",
            description="",
            details_url="https://luximmo.bg/imot.html",
            ref_no="",
            agency_name="Luximmo",
        )
        result = transformer.transform(raw)
        assert result.city == ""
        assert result.neighborhood == ""


class TestLuximmoExtractorNewFields:
    """Test extraction of new fields: total_floors_text, raw_link_description, num_photos."""

    @pytest.fixture
    def extractor(self):
        return LuximmoExtractor()

    def test_extract_total_floors_text(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-dis">
                <p class="text-muted"> Площ: <span class="text-dark">207.43 м²</span></p>
                <p class="text-muted"> Етаж: <span class="text-dark">2</span></p>
                <p class="text-muted"> Етажност: <span class="text-dark">5</span></p>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == "5"
        assert listings[0].floor_text == "2"

    def test_extract_total_floors_text_missing(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-dis">Площ: 95.5 м Етаж: 3</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == ""

    def test_extract_raw_link_description(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-img" title="Ексклузивен апартамент в Gloria Palace - LUXIMMO">
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == "Ексклузивен апартамент в Gloria Palace - LUXIMMO"

    def test_extract_raw_link_description_missing(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == ""

    def test_extract_num_photos_from_counter(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="counter-wrapper-card">
                <span class="counterCard">
                    <span class="firstNum">1</span><span> / </span><span class="lastNum">23</span>
                </span>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 23

    def test_extract_num_photos_from_slick_slides(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="slick-slide"></div>
            <div class="slick-slide"></div>
            <div class="slick-slide"></div>
            <div class="slick-slide"></div>
            <div class="slick-slide"></div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 5

    def test_extract_num_photos_fallback_to_card_img(self, extractor):
        html = """
        <div class="card mb-4">
            <a class="card-url" href="https://luximmo.bg/imot-123.html">Link</a>
            <h4 class="card-title">Апартамент</h4>
            <div class="card-img"></div>
            <div class="card-img"></div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 2


class TestLuximmoTransformTotalFloors:
    """Test transformer handling of total_floors field for Luximmo."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_with_total_floors(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="430 000 €",
            title="продава Четиристаен апартамент",
            location_text="гр. София / кв. Горна баня",
            area_text="207.43 м²",
            floor_text="2",
            total_floors_text="5",
            description="",
            details_url="https://www.luximmo.bg/za-prodajba/imot-43445.html",
            ref_no="43445",
            agency_name="Luximmo",
            num_photos=23,
        )
        result = transformer.transform(raw)

        assert result.floor == "2"
        assert result.total_floors == "5"
        assert result.num_photos == 23

    def test_transform_without_total_floors(self, transformer):
        raw = RawListing(
            site="luximmo",
            price_text="185000 €",
            title="продава Тристаен апартамент",
            location_text="гр. София / кв. Център",
            area_text="95.5 м",
            floor_text="3",
            description="",
            details_url="https://www.luximmo.bg/za-prodajba/imot-43445.html",
            ref_no="43445",
            agency_name="Luximmo",
            num_photos=5,
        )
        result = transformer.transform(raw)

        assert result.floor == "3"
        assert result.total_floors is None
