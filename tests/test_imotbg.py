import pytest
from bs4 import BeautifulSoup

from src.sites.imotbg import ImotBgParser, extract_photo_count


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
    def test_extract_photo_count(self):
        assert extract_photo_count("и 13 снимки") == 13

    def test_extract_photo_count_single(self):
        assert extract_photo_count("1 снимка") == 1

    def test_extract_photo_count_none(self):
        assert extract_photo_count("Повече детайли") is None

    def test_extract_photo_count_empty(self):
        assert extract_photo_count("") is None

    def test_extract_photo_count_null(self):
        assert extract_photo_count(None) is None


class TestImotBgParserConfig:
    def test_config_values(self):
        parser = ImotBgParser()
        assert parser.config.name == "imotbg"
        assert parser.config.base_url == "https://www.imot.bg"
        assert parser.config.encoding == "windows-1251"
        assert parser.config.rate_limit_seconds == 1.0


class TestImotBgParserBuildUrls:
    def test_build_urls(self):
        config = {
            "urls": [
                {"url": "https://imot.bg/search1", "name": "Search 1"},
                {"url": "https://imot.bg/search2", "name": "Search 2"},
            ]
        }
        urls = ImotBgParser.build_urls(config)
        assert urls == [
            {"url": "https://imot.bg/search1", "name": "Search 1"},
            {"url": "https://imot.bg/search2", "name": "Search 2"},
        ]

    def test_build_urls_empty(self):
        assert ImotBgParser.build_urls({}) == []


class TestImotBgParserExtractListings:
    @pytest.fixture
    def parser(self):
        return ImotBgParser()

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
        assert listings[0]["title"] == "Продава 2-СТАЕН"

    def test_extract_listing_location(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["location"] == "град София, Лозенец"

    def test_extract_listing_details_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["details_url"] == "//www.imot.bg/obiava-123-prodava-dvustaen"

    def test_extract_listing_photos_text(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert "13 снимки" in listings[0]["photos_text"]

    def test_extract_listing_contact_info(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["contact_info"] == "0888123456"

    def test_extract_listing_agency_name(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency_name"] == "Агенция Имоти"

    def test_extract_listing_agency_url(self, parser, soup):
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency_url"] == "//agency.imot.bg"


class TestImotBgParserTransform:
    @pytest.fixture
    def parser(self):
        return ImotBgParser()

    def test_transform_listing(self, parser):
        raw = {
            "price_text": "179 000 €350 093.57 лв.",
            "title": "Продава 2-СТАЕН",
            "location": "град София, Лозенец",
            "description": "Описание, тел.: 0888123456",
            "details_url": "//www.imot.bg/obiava-123",
            "photos_text": "и 13 снимки",
            "contact_info": "0888123456",
            "agency_name": "Агенция",
            "agency_url": "//agency.imot.bg",
        }
        result = parser.transform_listing(raw)

        assert result.site == "imotbg"
        assert result.price == 179000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.offer_type == "продава"
        assert result.num_photos == 13
        assert result.details_url == "https://www.imot.bg/obiava-123"


class TestImotBgParserPagination:
    @pytest.fixture
    def parser(self):
        return ImotBgParser()

    def test_get_next_page_url_with_query(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia?raioni=123"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imot.bg/obiavi/prodazhbi/sofia/p-2?raioni=123"

    def test_get_next_page_url_without_query(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url == "https://www.imot.bg/obiavi/prodazhbi/sofia/p-2"

    def test_get_next_page_url_existing_page(self, parser):
        soup = BeautifulSoup(SAMPLE_PAGE_HTML, "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia/p-2?raioni=123"
        next_url = parser.get_next_page_url(soup, url, 3)

        assert next_url == "https://www.imot.bg/obiavi/prodazhbi/sofia/p-3?raioni=123"

    def test_get_next_page_url_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        url = "https://www.imot.bg/obiavi/prodazhbi/sofia"
        next_url = parser.get_next_page_url(soup, url, 2)

        assert next_url is None


class TestImotBgParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return ImotBgParser()

    def test_extract_listings_no_items(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 0

    def test_extract_listing_missing_title(self, parser):
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
        listings = list(parser.extract_listings(soup))
        assert len(listings) == 1
        assert listings[0]["title"] == ""
        assert listings[0]["location"] == ""

    def test_extract_listing_missing_price(self, parser):
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
        listings = list(parser.extract_listings(soup))
        assert listings[0]["price_text"] == ""

    def test_extract_listing_missing_photos_link(self, parser):
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
        listings = list(parser.extract_listings(soup))
        assert listings[0]["photos_text"] == ""

    def test_extract_listing_missing_agency(self, parser):
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
        listings = list(parser.extract_listings(soup))
        assert listings[0]["agency_name"] == ""
        assert listings[0]["agency_url"] is None

    def test_extract_contact_from_description_no_phone(self, parser):
        assert parser._extract_contact_from_description("No phone here") == ""

    def test_extract_contact_from_description_with_phone(self, parser):
        assert parser._extract_contact_from_description("Info тел.: 0888123456") == "0888123456"

    def test_extract_contact_from_description_multiple_phones(self, parser):
        assert parser._extract_contact_from_description("тел.: 111 тел.: 222") == "222"

    def test_transform_listing_bgn(self, parser):
        raw = {
            "price_text": "250 000 лв.",
            "title": "Продава 3-СТАЕН",
            "location": "град Пловдив, Център",
            "description": "Test",
            "details_url": "//www.imot.bg/obiava-456",
            "photos_text": "",
            "contact_info": "",
            "agency_name": "",
            "agency_url": None,
        }
        result = parser.transform_listing(raw)

        assert result.price == 250000.0
        assert result.currency == "BGN"
        assert result.num_photos is None

    def test_transform_listing_rent(self, parser):
        raw = {
            "price_text": "500 EUR",
            "title": "Под наем 2-СТАЕН",
            "location": "София, Център",
            "description": "",
            "details_url": "//www.imot.bg/obiava-123",
            "photos_text": "",
            "contact_info": "",
            "agency_name": "",
            "agency_url": None,
        }
        result = parser.transform_listing(raw)

        assert result.offer_type == "наем"
        assert result.property_type == "двустаен"

    def test_transform_listing_missing_location(self, parser):
        raw = {
            "price_text": "100 EUR",
            "title": "Test",
            "location": "",
            "description": "",
            "details_url": "//www.imot.bg/obiava-123",
            "photos_text": "",
            "contact_info": "",
            "agency_name": "",
            "agency_url": None,
        }
        result = parser.transform_listing(raw)

        assert result.city == ""
        assert result.neighborhood == ""

    def test_pagination_page_one(self, parser):
        soup = BeautifulSoup("<html><body><div class='item'></div></body></html>", "html.parser")
        url = "https://www.imot.bg/obiavi/sofia"
        next_url = parser.get_next_page_url(soup, url, 1)

        assert next_url == "https://www.imot.bg/obiavi/sofia/p-1"

    def test_extract_photo_count_variations(self):
        assert extract_photo_count("и 5 снимки") == 5
        assert extract_photo_count("Повече детайли и 20 снимки") == 20
        assert extract_photo_count("5 снимка") == 5

    def test_extract_title_and_location_no_location_elem(self, parser):
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
        title, location = parser._extract_title_and_location(item)
        assert title == "Продава апартамент"
        assert location == ""
