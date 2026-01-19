import pytest

from src.sites.homesbg import HomesBgParser


SAMPLE_API_RESPONSE = {
    "searchCriteria": {"typeId": "ApartmentSell"},
    "hasMoreItems": True,
    "result": [
        {
            "id": 12345,
            "title": "Двустаен апартамент",
            "description": "Описание на имота",
            "location": "Лозенец, София",
            "price": {"value": 150000, "currency": "EUR", "pricePerSquareMeter": "2500 €/кв.м"},
            "viewHref": "/offer/12345",
            "photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
            "time": "2024-01-15",
        },
        {
            "id": 67890,
            "title": "Тристаен апартамент",
            "description": "Друго описание",
            "location": "Център, Пловдив",
            "price": {"value": 200000, "currency": "BGN"},
            "viewHref": "/offer/67890",
            "photos": [],
            "time": "2024-01-14",
        },
    ],
}


class TestHomesBgParserConfig:
    def test_config_values(self):
        parser = HomesBgParser()
        assert parser.config.name == "homesbg"
        assert parser.config.base_url == "https://www.homes.bg"
        assert parser.config.source_type == "json"
        assert parser.config.rate_limit_seconds == 2.0


class TestHomesBgParserBuildUrls:
    def test_build_urls_with_urls(self):
        config = {
            "urls": [
                {"url": "https://homes.bg/search1", "name": "Search 1"},
                {"url": "https://homes.bg/search2", "name": "Search 2"},
            ]
        }
        urls = HomesBgParser.build_urls(config)

        assert len(urls) == 2
        assert urls[0] == {"url": "https://homes.bg/search1", "name": "Search 1"}
        assert urls[1] == {"url": "https://homes.bg/search2", "name": "Search 2"}

    def test_build_urls_empty(self):
        urls = HomesBgParser.build_urls({})
        assert urls == []


class TestHomesBgParserExtractListings:
    @pytest.fixture
    def parser(self):
        return HomesBgParser()

    def test_extract_listings_count(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert len(listings) == 2

    def test_extract_listing_title(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["title"] == "Двустаен апартамент"

    def test_extract_listing_description(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["description"] == "Описание на имота"

    def test_extract_listing_city(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["city"] == "София"

    def test_extract_listing_neighborhood(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["neighborhood"] == "Лозенец"

    def test_extract_listing_price_value(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["price_value"] == 150000

    def test_extract_listing_price_currency(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["price_currency"] == "EUR"

    def test_extract_listing_price_per_m2(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["price_per_m2"] == "2500 €/кв.м"

    def test_extract_listing_details_url(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["details_url"] == "/offer/12345"

    def test_extract_listing_num_photos(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["num_photos"] == 3
        assert listings[1]["num_photos"] == 0

    def test_extract_listing_offer_type_sell(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["offer_type"] == "продава"

    def test_extract_listing_offer_type_rent(self, parser):
        data = {
            "searchCriteria": {"typeId": "ApartmentRent"},
            "result": [{"id": 1, "location": "", "price": {}}],
        }
        listings = list(parser.extract_listings(data))
        assert listings[0]["offer_type"] == "наем"

    def test_extract_listing_ref_no(self, parser):
        listings = list(parser.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0]["ref_no"] == "12345"


class TestHomesBgParserTransform:
    @pytest.fixture
    def parser(self):
        return HomesBgParser()

    def test_transform_listing(self, parser):
        raw = {
            "title": "Двустаен апартамент",
            "description": "Описание",
            "city": "София",
            "neighborhood": "Лозенец",
            "price_value": 150000,
            "price_currency": "EUR",
            "price_per_m2": "2500 €/кв.м",
            "details_url": "/offer/12345",
            "num_photos": 3,
            "time": "2024-01-15",
            "offer_type": "продава",
            "ref_no": "12345",
        }
        result = parser.transform_listing(raw)

        assert result.site == "homesbg"
        assert result.price == 150000.0
        assert result.currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.details_url == "https://www.homes.bg/offer/12345"


class TestHomesBgParserPagination:
    @pytest.fixture
    def parser(self):
        return HomesBgParser()

    def test_get_total_pages(self, parser):
        assert parser.get_total_pages({}) == 30

    def test_get_next_page_url_has_more(self, parser):
        data = {"hasMoreItems": True}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell"
        next_url = parser.get_next_page_url(data, url, 2)

        assert "startIndex=100" in next_url
        assert "stopIndex=200" in next_url

    def test_get_next_page_url_no_more(self, parser):
        data = {"hasMoreItems": False}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell"
        next_url = parser.get_next_page_url(data, url, 2)

        assert next_url is None

    def test_get_next_page_url_strips_existing_index(self, parser):
        data = {"hasMoreItems": True}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell&startIndex=0&stopIndex=100"
        next_url = parser.get_next_page_url(data, url, 2)

        assert "startIndex=100" in next_url
        assert "stopIndex=200" in next_url
        assert next_url.count("startIndex") == 1


class TestHomesBgParserHelpers:
    @pytest.fixture
    def parser(self):
        return HomesBgParser()

    def test_parse_location(self, parser):
        city, neighborhood = parser._parse_location("Лозенец, София")
        assert city == "София"
        assert neighborhood == "Лозенец"

    def test_parse_location_no_city(self, parser):
        city, neighborhood = parser._parse_location("Лозенец")
        assert city == ""
        assert neighborhood == "Лозенец"

    def test_parse_location_empty(self, parser):
        city, neighborhood = parser._parse_location("")
        assert city == ""
        assert neighborhood == ""

    def test_parse_location_none(self, parser):
        city, neighborhood = parser._parse_location(None)
        assert city == ""
        assert neighborhood == ""

    def test_determine_offer_type_sell(self, parser):
        assert parser._determine_offer_type({"typeId": "ApartmentSell"}) == "продава"

    def test_determine_offer_type_rent(self, parser):
        assert parser._determine_offer_type({"typeId": "ApartmentRent"}) == "наем"

    def test_determine_offer_type_empty(self, parser):
        assert parser._determine_offer_type({}) == "наем"
