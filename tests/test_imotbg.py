import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.imotbg import ImotBgExtractor

SAMPLE_LISTING_HTML = """
<div class="item TOP" id="ida123">
    <div class="photo">
        <a class="image saveSlink" href="//www.imot.bg/obiava-123-prodava-dvustaen">
            <img class="pic" src="//cdn.imot.bg/photo.jpg"/>
        </a>
    </div>
    <div class="text">
        <div class="zaglavie">
            <a class="title saveSlink" href="//www.imot.bg/obiava-123-prodava-dvustaen">
                Продава 2-СТАЕН<location>град София, Лозенец</location>
            </a>
            <div class="price">
                <div>179 000 €<br/>350 093.57 лв.</div>
            </div>
        </div>
        <div class="info">
            56 кв.м, 6-ти ет. от 8, ТЕЦ, Описание на имота..., тел.: 0888123456
        </div>
        <div class="seller">
            <div class="logo">
                <a href="//agency.imot.bg" target="_blank">
                    <img alt="лого Агенция" src="//www.imot.bg/images/logos/med/agency.pic"/>
                </a>
            </div>
            <div class="sInfo">
                <div class="name">
                    <a href="//agency.imot.bg" target="_blank">Агенция Имоти</a>
                </div>
            </div>
        </div>
    </div>
    <div class="links">
        <a class="photos saveSlink" href="//www.imot.bg/obiava-123">Повече детайли <strong>и 13 снимки</strong></a>
    </div>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
<span class="pageNumbersInfo">Обяви 1-24 от общо 1234</span>
{SAMPLE_LISTING_HTML}
<div class="item" id="ida456">
    <div class="text">
        <div class="zaglavie">
            <a class="title saveSlink" href="//www.imot.bg/obiava-456">
                Продава 3-СТАЕН<location>град Пловдив, Център</location>
            </a>
            <div class="price">
                <div>250 000 лв.</div>
            </div>
        </div>
        <div class="info">
            80 кв.м, описание, тел.: 0877654321
        </div>
    </div>
    <div class="links">
        <a class="photos saveSlink" href="//www.imot.bg/obiava-456">Повече детайли</a>
    </div>
</div>
</body>
</html>
"""


class TestExtractPhotoCount:
    @pytest.fixture
    def extractor(self):
        return ImotBgExtractor()

    def test_extract_photo_count(self, extractor):
        assert extractor._extract_photo_count("и 13 снимки") == 13

    def test_extract_photo_count_single(self, extractor):
        assert extractor._extract_photo_count("1 снимка") == 1

    def test_extract_photo_count_none(self, extractor):
        assert extractor._extract_photo_count("Повече детайли") is None

    def test_extract_photo_count_empty(self, extractor):
        assert extractor._extract_photo_count("") is None

    def test_extract_photo_count_null(self, extractor):
        assert extractor._extract_photo_count(None) is None


class TestTransformerExtractArea:
    """Test area extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_standard_format(self, transformer):
        assert transformer._extract_area("56 кв.м, 6-ти ет.") == 56.0

    def test_with_decimal(self, transformer):
        assert transformer._extract_area("80.5 кв.м") == 80.5

    def test_with_comma_decimal(self, transformer):
        assert transformer._extract_area("80,5 кв.м") == 80.5

    def test_no_match(self, transformer):
        assert transformer._extract_area("No area here") is None

    def test_empty(self, transformer):
        assert transformer._extract_area("") is None

    def test_none(self, transformer):
        assert transformer._extract_area(None) is None


class TestTransformerExtractFloor:
    """Test floor extraction via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_ordinal_format(self, transformer):
        assert transformer._extract_floor("6-ти ет. от 8") == "6"

    def test_prefix_format(self, transformer):
        assert transformer._extract_floor("ет. 3") == "3"

    def test_suffix_format(self, transformer):
        assert transformer._extract_floor("3 ет.") == "3"

    def test_no_match(self, transformer):
        assert transformer._extract_floor("No floor here") == ""

    def test_empty(self, transformer):
        assert transformer._extract_floor("") == ""

    def test_none(self, transformer):
        assert transformer._extract_floor(None) == ""


class TestExtractRefFromId:
    @pytest.fixture
    def extractor(self):
        return ImotBgExtractor()

    def test_ida_format(self, extractor):
        assert extractor._extract_ref_from_id("ida123") == "123"

    def test_id_format(self, extractor):
        assert extractor._extract_ref_from_id("id456") == "456"

    def test_no_match(self, extractor):
        assert extractor._extract_ref_from_id("notanid") == ""

    def test_empty(self, extractor):
        assert extractor._extract_ref_from_id("") == ""

    def test_none(self, extractor):
        assert extractor._extract_ref_from_id(None) == ""


class TestTransformerCalculatePricePerM2:
    """Test price per m2 calculation via Transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_standard_calculation(self, transformer):
        # 179000 EUR / 56 m2 = 3196.43
        result = transformer._calculate_price_per_m2(179000.0, 56.0)
        assert result == 3196.43

    def test_missing_price(self, transformer):
        result = transformer._calculate_price_per_m2(None, 56.0)
        assert result is None

    def test_missing_area(self, transformer):
        result = transformer._calculate_price_per_m2(179000.0, None)
        assert result is None

    def test_zero_area(self, transformer):
        result = transformer._calculate_price_per_m2(179000.0, 0)
        assert result is None


class TestImotBgExtractorConfig:
    def test_config_values(self):
        extractor = ImotBgExtractor()
        assert extractor.config.name == "imotbg"
        assert extractor.config.base_url == "https://www.imot.bg"
        assert extractor.config.encoding == "windows-1251"
        assert extractor.config.rate_limit_seconds == 1.0


class TestImotBgExtractorBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://imot.bg/search1", "name": "Search 1"},
                {"url": "https://imot.bg/search2", "name": "Search 2"},
            ]
        }
        urls = ImotBgExtractor.build_urls(config)
        assert urls == [
            {"url": "https://imot.bg/search1", "name": "Search 1"},
            {"url": "https://imot.bg/search2", "name": "Search 2"},
        ]

    def test_build_urls_empty(self):
        assert ImotBgExtractor.build_urls({}) == []


class TestImotBgExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return ImotBgExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "179 000 €" in listings[0].price_text

    def test_extract_listing_title(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].title == "Продава 2-СТАЕН"

    def test_extract_listing_location(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == "град София, Лозенец"

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].details_url == "https://www.imot.bg/obiava-123-prodava-dvustaen"

    def test_extract_listing_num_photos(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 13

    def test_extract_listing_agency_name(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == "Агенция Имоти"

    def test_extract_listing_agency_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        # //agency.imot.bg -> https://agency.imot.bg (protocol-relative URL)
        assert listings[0].agency_url == "https://agency.imot.bg"

    def test_extract_listing_ref_no(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].ref_no == "123"

    def test_extract_listing_total_offers(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_offers == 1234
        assert listings[1].total_offers == 1234  # Same for all listings on page

    def test_extract_listing_area_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "56 кв.м" in listings[0].area_text
        assert "6-ти ет." in listings[0].area_text


class TestImotBgTransform:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing(self, transformer):
        raw = RawListing(
            site="imotbg",
            price_text="179 000 €350 093.57 лв.",
            title="Продава 2-СТАЕН",
            location_text="град София, Лозенец",
            description="Описание, тел.: 0888123456",
            area_text="56 кв.м, 6-ти ет. от 8",
            floor_text="56 кв.м, 6-ти ет. от 8",
            details_url="https://www.imot.bg/obiava-123",
            num_photos=13,
            agency_name="Агенция",
            agency_url="https://agency.imot.bg",
            ref_no="123",
            total_offers=1234,
        )
        result = transformer.transform(raw)

        assert result.site == "imotbg"
        assert result.price == 179000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.num_photos == 13
        assert result.details_url == "https://www.imot.bg/obiava-123"
        assert result.area == 56.0
        assert result.floor == "6"
        assert result.ref_no == "123"
        assert result.total_offers == 1234
        # Price per m2: 179000 / 56 = 3196.43
        assert result.price_per_m2 == 3196.43


class TestImotBgExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return ImotBgExtractor()

    def test_get_next_page_url_with_query(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia?raioni=123"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imot.bg/obiavi/prodazhbi/sofia/p-2?raioni=123"

    def test_get_next_page_url_without_query(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imot.bg/obiavi/prodazhbi/sofia/p-2"

    def test_get_next_page_url_existing_page(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia/p-2?raioni=123"
        next_url = extractor.get_next_page_url(soup, url, 3)

        assert next_url == "https://www.imot.bg/obiavi/prodazhbi/sofia/p-3?raioni=123"

    def test_get_next_page_url_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url is None


class TestImotBgExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return ImotBgExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_listings_no_items(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, extractor):
        html = """
        <div class="item">
            <div class="text">
                <div class="zaglavie">
                    <div class="price"><div>100 EUR</div></div>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].title == ""
        assert listings[0].location_text == ""

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <div class="item">
            <div class="text">
                <div class="zaglavie">
                    <a class="title saveSlink" href="//www.imot.bg/obiava-123">
                        Продава 2-СТАЕН<location>София</location>
                    </a>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].price_text == ""

    def test_extract_listing_missing_photos_link(self, extractor):
        html = """
        <div class="item">
            <div class="text">
                <div class="zaglavie">
                    <a class="title saveSlink" href="//www.imot.bg/obiava-123">
                        Test<location>Sofia</location>
                    </a>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos is None

    def test_extract_listing_missing_agency(self, extractor):
        html = """
        <div class="item">
            <div class="text">
                <div class="zaglavie">
                    <a class="title saveSlink" href="//www.imot.bg/obiava-123">
                        Test<location>Sofia</location>
                    </a>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].agency_name == ""
        # prepend_base_url(None) returns ""
        assert listings[0].agency_url == ""

    def test_extract_contact_from_description_no_phone(self, extractor):
        assert extractor._extract_contact_from_description("No phone here") == ""

    def test_extract_contact_from_description_with_phone(self, extractor):
        assert extractor._extract_contact_from_description("Info тел.: 0888123456") == "0888123456"

    def test_extract_contact_from_description_multiple_phones(self, extractor):
        assert extractor._extract_contact_from_description("тел.: 111 тел.: 222") == "222"

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="imotbg",
            price_text="250 000 лв.",
            title="Продава 3-СТАЕН",
            location_text="град Пловдив, Център",
            description="Test",
            details_url="https://www.imot.bg/obiava-456",
        )
        result = transformer.transform(raw)

        # 250000 BGN / 1.9558 = 127825.43 EUR
        assert result.price == pytest.approx(127825.43, rel=0.01)
        assert result.original_currency == "BGN"
        assert result.num_photos is None

    def test_transform_listing_rent(self, transformer):
        raw = RawListing(
            site="imotbg",
            price_text="500 EUR",
            title="Под наем 2-СТАЕН",
            location_text="София, Център",
            details_url="https://www.imot.bg/obiava-123",
        )
        result = transformer.transform(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"

    def test_transform_listing_missing_location(self, transformer):
        raw = RawListing(
            site="imotbg",
            price_text="100 EUR",
            title="Test",
            location_text="",
            details_url="https://www.imot.bg/obiava-123",
        )
        result = transformer.transform(raw)

        assert result.city == ""
        assert result.neighborhood == ""

    def test_pagination_page_one(self, extractor):
        soup = BeautifulSoup("<html><body><div class='item'></div></body></html>", "html.parser")
        url = "https://www.imot.bg/obiavi/sofia"
        next_url = extractor.get_next_page_url(soup, url, 1)

        assert next_url == "https://www.imot.bg/obiavi/sofia/p-1"

    def test_extract_photo_count_variations(self, extractor):
        assert extractor._extract_photo_count("и 5 снимки") == 5
        assert extractor._extract_photo_count("Повече детайли и 20 снимки") == 20
        assert extractor._extract_photo_count("5 снимка") == 5

    def test_extract_title_and_location_no_location_elem(self, extractor):
        html = """
        <div class="item">
            <div class="text">
                <div class="zaglavie">
                    <a class="title saveSlink" href="//www.imot.bg/obiava-123">
                        Продава апартамент
                    </a>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        title, location = extractor._extract_title_and_location(item)
        assert title == "Продава апартамент"
        assert location == ""
