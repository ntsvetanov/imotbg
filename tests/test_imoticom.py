import pytest
from bs4 import BeautifulSoup

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.imoticom import ImotiComExtractor

SAMPLE_LISTING_HTML = """
<div class="item">
    <!--  10:07 часа от 29.12.2025-->
    <div class="title" style="line-height: 24px;">
        <span class="type">Продава  2-стаен</span>
        <span class="price" style="text-align: right;">179 000 €
            <br/>350 093,57 лв.
            <span style="font-weight: normal; font-size: 14px; color: #2a2a2a">
                <br/>Не се начислява ДДС
            </span>
        </span>
    </div>
    <a href="https://www.imoti.com/obiava/22699838/prodava-2-staen-grad-sofiya-belite-brezi"></a>
    <div class="photo" alt="Продава  2-стаен град София, Белите брези">
        <img src="//imotstatic4.focus.bg/imot/photo.jpg" title="Продажба" alt="Продажба"/>
    </div>
    <div class="adType"></div>
    <div class="info">
        <div class="location">
            град София, Белите брези<br/>
            56 кв.м, ет. 3
        </div>
        6-ти ет., ТЕЦ, UnitedArts Real Estate предлага двустаен апартамент...
        <div class="phones">
            тел.: 00359882211412
        </div>
        <div class="controls">
            <button class="note_btn">Добави в Бележника</button>
        </div>
    </div>
</div>
"""

SAMPLE_PAGE_HTML = f"""
<html>
<body>
<div class="list">
{SAMPLE_LISTING_HTML}
<div class="item">
    <!--  15:44 часа от днес-->
    <div class="title">
        <span class="type">Продава  3-стаен</span>
        <span class="price">250 000 лв.</span>
    </div>
    <a href="https://www.imoti.com/obiava/123456/prodava-3-staen-grad-plovdiv-centar"></a>
    <div class="photo">
        <img src="//photo.jpg"/>
    </div>
    <div class="info">
        <div class="location">
            град Пловдив, Център<br/>
            85 кв.м, етаж 5
        </div>
        Агенция за недвижими имоти Vice Real Estate представя имота...
        <div class="phones">
            тел.: 0877654321
        </div>
    </div>
</div>
</div>
<div>
    <strong>1</strong> - <strong>20</strong> от общо <strong>2456</strong> обяви<br>
</div>
<span class="paging">
    <a href="" class="now">1</a>
    <a href="/prodazhbi/grad-sofiya/dvustaini/page-2?sraion=123~">2</a>
    <a href="/prodazhbi/grad-sofiya/dvustaini/page-3?sraion=123~">3</a>
    <a href="/prodazhbi/grad-sofiya/dvustaini/page-4?sraion=123~" class="big">Напред</a>
    <a href="/prodazhbi/grad-sofiya/dvustaini/page-10?sraion=123~" class="big">Последна</a>
</span>
</body>
</html>
"""


class TestImotiComExtractorConfig:
    def test_config_values(self):
        extractor = ImotiComExtractor()
        assert extractor.config.name == "imoticom"
        assert extractor.config.base_url == "https://www.imoti.com"
        assert extractor.config.encoding == "utf-8"
        assert extractor.config.rate_limit_seconds == 1.0


class TestImotiComExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listings_returns_raw_listings(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert all(isinstance(listing, RawListing) for listing in listings)

    def test_extract_listing_price_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "179 000 €" in listings[0].price_text

    def test_extract_listing_title(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].title == "Продава  2-стаен"

    def test_extract_listing_location_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].location_text == "град София, Белите брези"

    def test_extract_listing_area_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].area_text == "56 кв.м"

    def test_extract_listing_floor_text(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == "3"

    def test_extract_listing_details_url(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert (
            listings[0].details_url == "https://www.imoti.com/obiava/22699838/prodava-2-staen-grad-sofiya-belite-brezi"
        )

    def test_extract_listing_description(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "UnitedArts Real Estate" in listings[0].description

    def test_extract_listing_ref_no(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].ref_no == "22699838"
        assert listings[1].ref_no == "123456"

    def test_extract_listing_total_offers(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_offers == 2456
        assert listings[1].total_offers == 2456  # Same for all listings on page

    def test_extract_listing_num_photos(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].num_photos == 1
        assert listings[1].num_photos == 1

    def test_extract_listing_agency_name(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert "UnitedArts Real Estate" in listings[0].agency_name
        assert "Vice Real Estate" in listings[1].agency_name

    def test_extract_listing_site(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        assert listings[0].site == "imoticom"

    def test_extract_listings_no_list_container(self, extractor):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 0


class TestTransformerWithImotiComData:
    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing_eur(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €350 093,57 лв.Не се начислява ДДС",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="ет. 3",
            description="Описание на имота",
            details_url="https://www.imoti.com/obiava/123/prodava-2-staen",
            ref_no="123",
            total_offers=2456,
            num_photos=1,
            agency_name="Test Agency",
            agency_url="",
        )
        result = transformer.transform(raw)

        assert result.site == "imoticom"
        assert result.price == 179000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Белите брези"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.area == 56.0
        assert result.floor == "3"
        assert result.details_url == "https://www.imoti.com/obiava/123/prodava-2-staen"

    def test_transform_listing_bgn(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="250 000 лв.",
            title="Продава  3-стаен",
            location_text="град Пловдив, Център",
            area_text="85 кв.м",
            floor_text="5",
            description="Описание",
            details_url="https://www.imoti.com/obiava/456/prodava-3-staen",
            ref_no="456",
            total_offers=100,
            num_photos=1,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)

        assert result.site == "imoticom"
        # Price converted from BGN to EUR (250000 / 1.9558)
        assert result.price == pytest.approx(127823.85, rel=0.01)
        assert result.original_currency == "BGN"
        assert result.city == "Пловдив"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"

    def test_transform_listing_with_floor(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="5 ет.",
            description="",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=0,
            num_photos=0,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)

        assert result.floor == "5"

    def test_transform_listing_with_search_url(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="3",
            description="",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=2456,
            num_photos=1,
            agency_name="",
            agency_url="",
            search_url="https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini",
        )
        result = transformer.transform(raw)

        assert result.search_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini"

    def test_transform_listing_missing_fields(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="",
            title="",
            location_text="",
            area_text="",
            floor_text="",
            description="",
            details_url="",
            ref_no="",
            total_offers=0,
            num_photos=0,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)
        assert result.price is None
        assert result.original_currency == ""
        assert result.city == ""
        assert result.neighborhood == ""
        assert result.ref_no == ""
        assert result.num_photos == 0

    def test_transform_listing_rent_offer(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="500 EUR",
            title="Под наем 2-стаен",
            location_text="град София, Център",
            area_text="50 кв.м",
            floor_text="",
            description="Test",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=0,
            num_photos=0,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)
        assert result.offer_type == "наем"

    def test_transform_price_per_m2(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="3",
            description="",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=2456,
            num_photos=1,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)
        # 179000 / 56 = 3196.43
        assert result.price_per_m2 == pytest.approx(3196.43, rel=0.01)


class TestImotiComExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    def test_get_total_pages(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        assert extractor.get_total_pages(soup) == 10

    def test_get_total_pages_no_paginator(self, extractor):
        soup = BeautifulSoup("<html><body><div class='list'></div></body></html>", "html.parser")
        assert extractor.get_total_pages(soup) == extractor.config.max_pages

    def test_get_next_page_url_with_query(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini?sraion=86~80~"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-2?sraion=86~80~"

    def test_get_next_page_url_without_query(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-2"

    def test_get_next_page_url_existing_page(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-2?sraion=86~"
        next_url = extractor.get_next_page_url(soup, url, 3)

        assert next_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-3?sraion=86~"

    def test_get_next_page_url_exceeds_total(self, extractor):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini?sraion=86~"
        next_url = extractor.get_next_page_url(soup, url, 11)

        assert next_url is None

    def test_get_next_page_url_no_items(self, extractor):
        soup = BeautifulSoup("<html><body><div class='list'></div></body></html>", "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini"
        next_url = extractor.get_next_page_url(soup, url, 2)

        assert next_url is None


class TestImotiComExtractorHelpers:
    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    def test_get_location(self, extractor):
        html = """
        <div class="item">
            <div class="info">
                <div class="location">
                    град София, Лозенец<br/>
                    75 кв.м
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        assert extractor._get_location(item) == "град София, Лозенец"

    def test_get_location_info(self, extractor):
        html = """
        <div class="item">
            <div class="info">
                <div class="location">
                    град София, Лозенец<br/>
                    75 кв.м
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        location_info = extractor._get_location_info(item)
        assert "град София, Лозенец" in location_info
        assert "75 кв.м" in location_info

    def test_get_location_no_div(self, extractor):
        html = """<div class="item"><div class="info"></div></div>"""
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        assert extractor._get_location(item) == ""

    def test_get_location_info_no_div(self, extractor):
        html = """<div class="item"><div class="info"></div></div>"""
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        assert extractor._get_location_info(item) == ""


class TestImotiComExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_listing_missing_price(self, extractor):
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="info">
                    <div class="location">град София</div>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].price_text == ""

    def test_extract_listing_missing_location(self, extractor):
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                    <span class="price">100 000 EUR</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="info"></div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].location_text == ""
        assert listings[0].area_text == ""

    def test_pagination_only_next_no_last(self, extractor):
        html = """
        <html><body>
        <div class="list"><div class="item"></div></div>
        <span class="paging">
            <a href="" class="now">1</a>
            <a href="/page-2" class="big">Напред</a>
        </span>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert extractor.get_total_pages(soup) == extractor.config.max_pages

    def test_get_next_page_url_page_one(self, extractor):
        html = """
        <html><body>
        <div class="list"><div class="item"></div></div>
        <a href="/page-5" class="big">Последна</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        url = "https://www.imoti.com/search"
        next_url = extractor.get_next_page_url(soup, url, 1)
        assert next_url == "https://www.imoti.com/search/page-1"


class TestTransformerLocationParsing:
    """Test the Transformer's location parsing with imoti.com-style data."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_parse_city_from_location(self, transformer):
        raw = RawListing(
            site="imoticom",
            location_text="град София, Белите брези",
        )
        result = transformer.transform(raw)
        assert result.city == "София"

    def test_parse_city_no_neighborhood(self, transformer):
        raw = RawListing(
            site="imoticom",
            location_text="град София",
        )
        result = transformer.transform(raw)
        assert result.city == "София"

    def test_parse_empty_location(self, transformer):
        raw = RawListing(
            site="imoticom",
            location_text="",
        )
        result = transformer.transform(raw)
        assert result.city == ""

    def test_parse_neighborhood(self, transformer):
        raw = RawListing(
            site="imoticom",
            location_text="град София, Белите брези",
        )
        result = transformer.transform(raw)
        assert result.neighborhood == "Белите брези"

    def test_parse_neighborhood_no_comma(self, transformer):
        raw = RawListing(
            site="imoticom",
            location_text="град София",
        )
        result = transformer.transform(raw)
        assert result.neighborhood == ""

    def test_city_multiple_commas(self, transformer):
        raw = RawListing(
            site="imoticom",
            location_text="град София, Лозенец, ул. Тест",
        )
        result = transformer.transform(raw)
        assert result.city == "София"


class TestTransformerAreaParsing:
    """Test the Transformer's area parsing with imoti.com-style data."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_area(self, transformer):
        raw = RawListing(
            site="imoticom",
            area_text="56 кв.м",
        )
        result = transformer.transform(raw)
        assert result.area == 56.0

    def test_extract_area_with_space(self, transformer):
        raw = RawListing(
            site="imoticom",
            area_text="100 кв.м",
        )
        result = transformer.transform(raw)
        assert result.area == 100.0

    def test_extract_area_without_space(self, transformer):
        raw = RawListing(
            site="imoticom",
            area_text="100кв.м",
        )
        result = transformer.transform(raw)
        assert result.area == 100.0

    def test_extract_area_empty(self, transformer):
        raw = RawListing(
            site="imoticom",
            area_text="",
        )
        result = transformer.transform(raw)
        assert result.area is None


class TestTransformerFloorParsing:
    """Test the Transformer's floor parsing with imoti.com-style data."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_floor_et(self, transformer):
        raw = RawListing(
            site="imoticom",
            floor_text="ет. 3",
        )
        result = transformer.transform(raw)
        assert result.floor == "3"

    def test_extract_floor_etaj(self, transformer):
        raw = RawListing(
            site="imoticom",
            floor_text="Етаж: 5",
        )
        result = transformer.transform(raw)
        assert result.floor == "5"

    def test_extract_floor_empty(self, transformer):
        raw = RawListing(
            site="imoticom",
            floor_text="",
        )
        result = transformer.transform(raw)
        assert result.floor == ""


class TestExtractTotalFloors:
    """Test the extract_total_floors method."""

    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    def test_extract_total_floors_etajnost(self, extractor):
        assert extractor.extract_total_floors("Етажност: 8") == "8"

    def test_extract_total_floors_etajnost_no_space(self, extractor):
        assert extractor.extract_total_floors("Етажност:12") == "12"

    def test_extract_total_floors_ot_pattern_etaja(self, extractor):
        assert extractor.extract_total_floors("3-ти от 8 етажа") == "8"

    def test_extract_total_floors_ot_pattern_et(self, extractor):
        assert extractor.extract_total_floors("5-ти от 10 ет.") == "10"

    def test_extract_total_floors_empty(self, extractor):
        assert extractor.extract_total_floors("") == ""

    def test_extract_total_floors_no_match(self, extractor):
        assert extractor.extract_total_floors("Апартамент в новострой") == ""

    def test_extract_total_floors_none(self, extractor):
        assert extractor.extract_total_floors(None) == ""


class TestImotiComExtractorNewFields:
    """Test extraction of raw_link_description and total_floors_text."""

    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_raw_link_description(self, extractor, soup):
        listings = list(extractor.extract_listings(soup))
        # First listing has alt="Продава  2-стаен град София, Белите брези"
        assert listings[0].raw_link_description == "Продава  2-стаен град София, Белите брези"

    def test_extract_raw_link_description_empty(self, extractor):
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                    <span class="price">100 000 EUR</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="photo">
                    <img src="test.jpg"/>
                </div>
                <div class="info">
                    <div class="location">град София</div>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].raw_link_description == ""

    def test_extract_total_floors_text_from_description(self, extractor):
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                    <span class="price">100 000 EUR</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="photo" alt="Test photo"></div>
                <div class="info">
                    <div class="location">град София<br/>56 кв.м</div>
                    Етажност: 8, ТЕЦ, Агенция предлага...
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == "8"

    def test_extract_total_floors_text_empty(self, extractor, soup):
        # SAMPLE_PAGE_HTML doesn't have etajnost info
        listings = list(extractor.extract_listings(soup))
        assert listings[0].total_floors_text == ""


class TestImotiComExtractFloorFromDescription:
    """Test extraction of floor from description when not in location."""

    @pytest.fixture
    def extractor(self):
        return ImotiComExtractor()

    def test_extract_floor_from_description_ordinal(self, extractor):
        """Test extracting floor from description with ordinal format (6-ти ет.)."""
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                    <span class="price">179 000 €</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="photo" alt="Test"></div>
                <div class="info">
                    <div class="location">град София, Белите брези<br/>56 кв.м</div>
                    6-ти ет., ТЕЦ, UnitedArts Real Estate предлага...
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0].floor_text == "6"

    def test_extract_floor_from_location_preferred(self, extractor):
        """Test that floor from location is used when available."""
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                    <span class="price">179 000 €</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="photo" alt="Test"></div>
                <div class="info">
                    <div class="location">град София, Белите брези<br/>56 кв.м, ет. 3</div>
                    6-ти ет., ТЕЦ, описание...
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        # Should use floor from location (3), not description (6)
        assert listings[0].floor_text == "3"

    def test_extract_floor_no_floor_info(self, extractor):
        """Test when no floor info is available anywhere."""
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                    <span class="price">179 000 €</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="photo" alt="Test"></div>
                <div class="info">
                    <div class="location">град София<br/>56 кв.м</div>
                    Описание без етаж
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(extractor.extract_listings(soup))
        assert listings[0].floor_text == ""


class TestImotiComTransformTotalFloors:
    """Test that total_floors is correctly passed through transformer."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_with_total_floors(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="3",
            total_floors_text="8",
            description="",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=2456,
            num_photos=1,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)
        assert result.total_floors == "8"

    def test_transform_with_empty_total_floors(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="3",
            total_floors_text="",
            description="",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=2456,
            num_photos=1,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)
        assert result.total_floors == ""

    def test_transform_with_none_total_floors(self, transformer):
        raw = RawListing(
            site="imoticom",
            price_text="179 000 €",
            title="Продава  2-стаен",
            location_text="град София, Белите брези",
            area_text="56 кв.м",
            floor_text="3",
            total_floors_text=None,
            description="",
            details_url="https://www.imoti.com/obiava/123",
            ref_no="123",
            total_offers=2456,
            num_photos=1,
            agency_name="",
            agency_url="",
        )
        result = transformer.transform(raw)
        assert result.total_floors is None
