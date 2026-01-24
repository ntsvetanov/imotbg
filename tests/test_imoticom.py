import pytest
from bs4 import BeautifulSoup

from src.sites.imoticom import (
    ImotiComParser,
    extract_area,
    extract_city_from_location as extract_city,
    extract_neighborhood_from_location as extract_neighborhood,
    extract_ref_from_url,
    calculate_price_per_m2,
)

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
            56 кв.м
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
            85 кв.м
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


class TestExtractHelpers:
    def test_extract_city(self):
        assert extract_city("град София, Белите брези") == "София"

    def test_extract_city_no_neighborhood(self):
        assert extract_city("град София") == "София"

    def test_extract_city_empty(self):
        assert extract_city("") == ""

    def test_extract_city_none(self):
        assert extract_city(None) == ""

    def test_extract_neighborhood(self):
        assert extract_neighborhood("град София, Белите брези") == "Белите брези"

    def test_extract_neighborhood_no_comma(self):
        assert extract_neighborhood("град София") == ""

    def test_extract_neighborhood_empty(self):
        assert extract_neighborhood("") == ""

    def test_extract_neighborhood_none(self):
        assert extract_neighborhood(None) == ""

    def test_extract_area(self):
        assert extract_area("град София, Белите брези\n56 кв.м") == "56 кв.м"

    def test_extract_area_no_area(self):
        assert extract_area("град София, Белите брези") == ""

    def test_extract_area_empty(self):
        assert extract_area("") == ""

    def test_extract_area_none(self):
        assert extract_area(None) == ""


class TestExtractRefFromUrl:
    def test_extract_ref_from_url(self):
        assert extract_ref_from_url("https://www.imoti.com/obiava/22699838/prodava-2-staen") == "22699838"

    def test_extract_ref_from_url_empty(self):
        assert extract_ref_from_url("") == ""

    def test_extract_ref_from_url_none(self):
        assert extract_ref_from_url(None) == ""

    def test_extract_ref_from_url_no_match(self):
        assert extract_ref_from_url("https://www.imoti.com/search") == ""


class TestCalculatePricePerM2:
    def test_calculate_price_per_m2(self):
        raw = {"price_text": "179 000 €", "location_info": "град София\n56 кв.м"}
        assert calculate_price_per_m2(raw) == "3196.43"

    def test_calculate_price_per_m2_no_price(self):
        raw = {"price_text": "", "location_info": "56 кв.м"}
        assert calculate_price_per_m2(raw) == ""

    def test_calculate_price_per_m2_no_area(self):
        raw = {"price_text": "179 000 €", "location_info": ""}
        assert calculate_price_per_m2(raw) == ""

    def test_calculate_price_per_m2_empty(self):
        assert calculate_price_per_m2({}) == ""


class TestImotiComParserConfig:
    def test_config_values(self):
        parser = ImotiComParser()
        assert parser.config.name == "imoticom"
        assert parser.config.base_url == "https://www.imoti.com"
        assert parser.config.encoding == "utf-8"
        assert parser.config.rate_limit_seconds == 1.0


class TestImotiComParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://imoti.com/search1", "name": "Search 1"},
                {"url": "https://imoti.com/search2", "name": "Search 2"},
            ]
        }
        urls = ImotiComParser.build_urls(config)
        assert urls == [
            {"url": "https://imoti.com/search1", "name": "Search 1"},
            {"url": "https://imoti.com/search2", "name": "Search 2"},
        ]

    def test_build_urls_empty(self):
        assert ImotiComParser.build_urls({}) == []


class TestImotiComParserExtractListings:
    @pytest.fixture
    def parser(self):
        return ImotiComParser()

    @pytest.fixture
    def soup(self):
        return BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")

    def test_extract_listings_count(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 2

    def test_extract_listing_price_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "179 000 €" in listings[0]["price_text"]

    def test_extract_listing_title(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["title"] == "Продава  2-стаен"

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == "град София, Белите брези"

    def test_extract_listing_location_info(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "56 кв.м" in listings[0]["location_info"]

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert (
            listings[0]["details_url"]
            == "https://www.imoti.com/obiava/22699838/prodava-2-staen-grad-sofiya-belite-brezi"
        )

    def test_extract_listing_contact_info(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["contact_info"] == "00359882211412"

    def test_extract_listing_description(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "UnitedArts Real Estate" in listings[0]["description"]

    def test_extract_listing_ref_no(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["ref_no"] == "22699838"
        assert listings[1]["ref_no"] == "123456"

    def test_extract_listing_time(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["time"] == "10:07 29.12.2025"
        assert listings[1]["time"] == "15:44 днес"

    def test_extract_listing_total_offers(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["total_offers"] == 2456
        assert listings[1]["total_offers"] == 2456  # Same for all listings on page

    def test_extract_listing_num_photos(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["num_photos"] == 1
        assert listings[1]["num_photos"] == 1

    def test_extract_listing_agency_name(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "UnitedArts Real Estate" in listings[0]["agency_name"]
        assert "Vice Real Estate" in listings[1]["agency_name"]

    def test_extract_listing_price_per_m2(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_per_m2"] == "3196.43"

    def test_extract_listings_no_list_container(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0


class TestImotiComParserTransform:
    @pytest.fixture
    def parser(self):
        return ImotiComParser()

    def test_transform_listing_eur(self, parser):
        raw = {
            "price_text": "179 000 €350 093,57 лв.Не се начислява ДДС",
            "title": "Продава  2-стаен",
            "location": "град София, Белите брези",
            "location_info": "град София, Белите брези\n56 кв.м",
            "description": "Описание на имота",
            "details_url": "https://www.imoti.com/obiava/123",
            "contact_info": "0888123456",
            "ref_no": "123",
            "total_offers": 2456,
            "time": "10:07 29.12.2025",
            "num_photos": 1,
            "agency_name": "Test Agency",
            "agency_url": "",
            "price_per_m2": "3196.43",
        }
        result = parser.transform_listing(raw)

        assert result.site == "imoticom"
        assert result.price == 179000.0
        assert result.currency == "EUR"
        assert result.without_dds is True
        assert result.city == "София"
        assert result.neighborhood == "Белите брези"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.area == "56 кв.м"
        assert result.details_url == "https://www.imoti.com/obiava/123"

    def test_transform_listing_bgn(self, parser):
        raw = {
            "price_text": "250 000 лв.",
            "title": "Продава  3-стаен",
            "location": "град Пловдив, Център",
            "location_info": "град Пловдив, Център\n85 кв.м",
            "description": "Описание",
            "details_url": "https://www.imoti.com/obiava/456",
            "contact_info": "0877654321",
            "ref_no": "456",
            "total_offers": 100,
            "time": "15:44 днес",
            "num_photos": 1,
            "agency_name": "",
            "agency_url": "",
            "price_per_m2": "2941.18",
        }
        result = parser.transform_listing(raw)

        assert result.site == "imoticom"
        assert result.price == 250000.0
        assert result.currency == "BGN"
        assert result.city == "Пловдив"
        assert result.neighborhood == "Център"
        assert result.property_type == "тристаен"


class TestImotiComParserPagination:
    @pytest.fixture
    def parser(self):
        return ImotiComParser()

    def test_get_total_pages(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        assert parser.get_total_pages(soup) == 10

    def test_get_total_pages_no_paginator(self, parser):
        soup = BeautifulSoup("<html><body><div class='list'></div></body></html>", "html.parser")
        assert parser.get_total_pages(soup) == parser.config.max_pages

    def test_get_next_page_url_with_query(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini?sraion=86~80~"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-2?sraion=86~80~"

    def test_get_next_page_url_without_query(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-2"

    def test_get_next_page_url_existing_page(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-2?sraion=86~"
        next_url = parser.get_next_page_url(soup, url, 3)

        assert next_url == "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini/page-3?sraion=86~"

    def test_get_next_page_url_exceeds_total(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini?sraion=86~"
        next_url = parser.get_next_page_url(soup, url, 11)

        assert next_url is None

    def test_get_next_page_url_no_items(self, parser):
        soup = BeautifulSoup("<html><body><div class='list'></div></body></html>", "html.parser")
        url = "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url is None


class TestImotiComParserHelpers:
    @pytest.fixture
    def parser(self):
        return ImotiComParser()

    def test_extract_location(self, parser):
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
        assert parser._extract_location(item) == "град София, Лозенец"

    def test_extract_location_info(self, parser):
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
        location_info = parser._extract_location_info(item)
        assert "град София, Лозенец" in location_info
        assert "75 кв.м" in location_info

    def test_extract_location_no_div(self, parser):
        html = """<div class="item"><div class="info"></div></div>"""
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        assert parser._extract_location(item) == ""

    def test_extract_location_info_no_div(self, parser):
        html = """<div class="item"><div class="info"></div></div>"""
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("div.item")
        assert parser._extract_location_info(item) == ""


class TestImotiComParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return ImotiComParser()

    def test_extract_listing_missing_price(self, parser):
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
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["price_text"] == ""

    def test_extract_listing_missing_location(self, parser):
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
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["location"] == ""
        assert listings[0]["location_info"] == ""

    def test_extract_listing_contact_without_prefix(self, parser):
        html = """
        <div class="list">
            <div class="item">
                <div class="title">
                    <span class="type">Продава 2-стаен</span>
                </div>
                <a href="https://www.imoti.com/obiava/123"></a>
                <div class="info">
                    <div class="phones">0888123456</div>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        listings = list(parser.extract_listings(soup))
        assert listings[0]["contact_info"] == "0888123456"

    def test_transform_listing_missing_fields(self, parser):
        raw = {
            "price_text": "",
            "title": "",
            "location": "",
            "location_info": "",
            "description": "",
            "details_url": "",
            "contact_info": "",
            "ref_no": "",
            "total_offers": 0,
            "time": "",
            "num_photos": 0,
            "agency_name": "",
            "agency_url": "",
            "price_per_m2": "",
        }
        result = parser.transform_listing(raw)
        assert result.price == 0.0
        assert result.currency == ""
        assert result.city == ""
        assert result.neighborhood == ""
        assert result.ref_no == ""
        assert result.num_photos == 0

    def test_transform_listing_rent_offer(self, parser):
        raw = {
            "price_text": "500 EUR",
            "title": "Под наем 2-стаен",
            "location": "град София, Център",
            "location_info": "град София, Център\n50 кв.м",
            "description": "Test",
            "details_url": "https://www.imoti.com/obiava/123",
            "contact_info": "",
            "ref_no": "123",
            "total_offers": 0,
            "time": "",
            "num_photos": 0,
            "agency_name": "",
            "agency_url": "",
            "price_per_m2": "10.0",
        }
        result = parser.transform_listing(raw)
        assert result.offer_type == "наем"

    def test_extract_area_with_space(self):
        assert extract_area("София\n100 кв.м") == "100 кв.м"

    def test_extract_area_without_space(self):
        assert extract_area("София\n100кв.м") == "100 кв.м"

    def test_extract_city_multiple_commas(self):
        assert extract_city("град София, Лозенец, ул. Тест") == "София"

    def test_extract_neighborhood_multiple_commas(self):
        assert extract_neighborhood("град София, Лозенец, ул. Тест") == "Лозенец"

    def test_pagination_only_next_no_last(self, parser):
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
        assert parser.get_total_pages(soup) == parser.config.max_pages

    def test_get_next_page_url_page_one(self, parser):
        html = """
        <html><body>
        <div class="list"><div class="item"></div></div>
        <a href="/page-5" class="big">Последна</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        url = "https://www.imoti.com/search"
        next_url = parser.get_next_page_url(soup, url, 1)
        assert next_url == "https://www.imoti.com/search/page-1"
