import pytest

from src.core.models import RawListing
from src.core.transformer import Transformer
from src.sites.homesbg import HomesBgExtractor

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


class TestHomesBgExtractorConfig:
    def test_config_values(self):
        extractor = HomesBgExtractor()
        assert extractor.config.name == "homesbg"
        assert extractor.config.base_url == "https://www.homes.bg"
        assert extractor.config.source_type == "json"
        assert extractor.config.rate_limit_seconds == 2.0


class TestHomesBgExtractorBuildUrls:
    def test_build_urls_with_urls(self):
        config = {
            "urls": [
                {"url": "https://homes.bg/search1", "name": "Search 1"},
                {"url": "https://homes.bg/search2", "name": "Search 2"},
            ]
        }
        urls = HomesBgExtractor.build_urls(config)

        assert len(urls) == 2
        assert urls[0] == {"url": "https://homes.bg/search1", "name": "Search 1"}
        assert urls[1] == {"url": "https://homes.bg/search2", "name": "Search 2"}

    def test_build_urls_empty(self):
        urls = HomesBgExtractor.build_urls({})
        assert urls == []


class TestHomesBgExtractorExtractListings:
    @pytest.fixture
    def extractor(self):
        return HomesBgExtractor()

    def test_extract_listings_count(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert len(listings) == 2

    def test_extract_listing_title(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert "Двустаен апартамент" in listings[0].title

    def test_extract_listing_description(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0].description == "Описание на имота"

    def test_extract_listing_location_text(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        # Location text is formatted for transformer
        assert "София" in listings[0].location_text
        assert "Лозенец" in listings[0].location_text

    def test_extract_listing_price_text(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert "150000" in listings[0].price_text
        assert "€" in listings[0].price_text

    def test_extract_listing_details_url(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0].details_url == "https://www.homes.bg/offer/12345"

    def test_extract_listing_num_photos(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0].num_photos == 3
        assert listings[1].num_photos == 0

    def test_extract_listing_title_contains_offer_type(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        # The offer type "продава" is prepended to title
        assert "продава" in listings[0].title.lower()

    def test_extract_listing_offer_type_rent(self, extractor):
        data = {
            "searchCriteria": {"typeId": "ApartmentRent"},
            "result": [{"id": 1, "location": "", "price": {}}],
        }
        listings = list(extractor.extract_listings(data))
        assert "наем" in listings[0].title.lower()

    def test_extract_listing_ref_no(self, extractor):
        listings = list(extractor.extract_listings(SAMPLE_API_RESPONSE))
        assert listings[0].ref_no == "12345"


class TestHomesBgExtractorTransform:
    @pytest.fixture
    def extractor(self):
        return HomesBgExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_transform_listing(self, extractor, transformer):
        raw = RawListing(
            site="homesbg",
            title="продава Двустаен апартамент",
            description="Описание",
            location_text="София, Лозенец",
            price_text="150000 €",
            details_url="https://www.homes.bg/offer/12345",
            num_photos=3,
            ref_no="12345",
        )
        result = transformer.transform(raw)

        assert result.site == "homesbg"
        assert result.price == 150000.0
        assert result.original_currency == "EUR"
        assert result.city == "София"
        assert result.neighborhood == "Лозенец"
        assert result.property_type == "двустаен"
        assert result.details_url == "https://www.homes.bg/offer/12345"


class TestHomesBgExtractorPagination:
    @pytest.fixture
    def extractor(self):
        return HomesBgExtractor()

    def test_get_total_pages(self, extractor):
        assert extractor.get_total_pages({}) == 30

    def test_get_next_page_url_has_more(self, extractor):
        data = {"hasMoreItems": True}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell"
        next_url = extractor.get_next_page_url(data, url, 2)

        assert "startIndex=100" in next_url
        assert "stopIndex=200" in next_url

    def test_get_next_page_url_no_more(self, extractor):
        data = {"hasMoreItems": False}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell"
        next_url = extractor.get_next_page_url(data, url, 2)

        assert next_url is None

    def test_get_next_page_url_strips_existing_index(self, extractor):
        data = {"hasMoreItems": True}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell&startIndex=0&stopIndex=100"
        next_url = extractor.get_next_page_url(data, url, 2)

        assert "startIndex=100" in next_url
        assert "stopIndex=200" in next_url
        assert next_url.count("startIndex") == 1


class TestHomesBgExtractorHelpers:
    @pytest.fixture
    def extractor(self):
        return HomesBgExtractor()

    def test_parse_location(self, extractor):
        city, neighborhood = extractor._parse_location("Лозенец, София")
        assert city == "София"
        assert neighborhood == "Лозенец"

    def test_parse_location_no_city(self, extractor):
        city, neighborhood = extractor._parse_location("Лозенец")
        assert city == ""
        assert neighborhood == "Лозенец"

    def test_parse_location_empty(self, extractor):
        city, neighborhood = extractor._parse_location("")
        assert city == ""
        assert neighborhood == ""

    def test_parse_location_none(self, extractor):
        city, neighborhood = extractor._parse_location(None)
        assert city == ""
        assert neighborhood == ""

    def test_determine_offer_type_sell(self, extractor):
        assert extractor._determine_offer_type({"typeId": "ApartmentSell"}) == "продава"

    def test_determine_offer_type_rent(self, extractor):
        assert extractor._determine_offer_type({"typeId": "ApartmentRent"}) == "наем"

    def test_determine_offer_type_empty(self, extractor):
        # When no typeId is provided, returns empty string
        assert extractor._determine_offer_type({}) == ""


class TestHomesBgExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return HomesBgExtractor()

    @pytest.fixture
    def transformer(self):
        return Transformer()

    def test_extract_listings_empty_result(self, extractor):
        data = {"searchCriteria": {}, "result": []}
        listings = list(extractor.extract_listings(data))
        assert len(listings) == 0

    def test_extract_listings_missing_result(self, extractor):
        data = {"searchCriteria": {}}
        listings = list(extractor.extract_listings(data))
        assert len(listings) == 0

    def test_extract_listings_missing_search_criteria(self, extractor):
        data = {"result": [{"id": 1, "location": "", "price": {}}]}
        listings = list(extractor.extract_listings(data))
        assert len(listings) == 1

    def test_extract_listing_missing_price_data(self, extractor):
        data = {"searchCriteria": {}, "result": [{"id": 1, "location": "Лозенец, София"}]}
        listings = list(extractor.extract_listings(data))
        assert listings[0].price_text == ""

    def test_extract_listing_empty_photos(self, extractor):
        data = {"searchCriteria": {}, "result": [{"id": 1, "location": "", "price": {}}]}
        listings = list(extractor.extract_listings(data))
        assert listings[0].num_photos == 0

    def test_extract_listing_missing_fields(self, extractor):
        data = {"searchCriteria": {}, "result": [{}]}
        listings = list(extractor.extract_listings(data))
        assert listings[0].title is None  # No offer type prefix when searchCriteria empty
        assert listings[0].description is None
        assert listings[0].ref_no == ""

    def test_transform_listing_missing_price(self, transformer):
        raw = RawListing(
            site="homesbg",
            title="Test",
            description="",
            location_text="",
            price_text="",
            details_url="/offer/123",
            num_photos=0,
            ref_no="123",
        )
        result = transformer.transform(raw)
        assert result.price is None

    def test_transform_listing_bgn_price(self, transformer):
        raw = RawListing(
            site="homesbg",
            title="Test",
            description="",
            location_text="",
            price_text="150000 лв",
            details_url="/offer/123",
            num_photos=0,
            ref_no="123",
        )
        result = transformer.transform(raw)
        # Price is converted from BGN to EUR
        assert result.price is not None
        assert result.original_currency == "BGN"

    def test_parse_location_multiple_commas(self, extractor):
        city, neighborhood = extractor._parse_location("Лозенец, София, България")
        assert city == "София"
        assert neighborhood == "Лозенец"

    def test_get_next_page_url_first_page(self, extractor):
        data = {"hasMoreItems": True}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell"
        next_url = extractor.get_next_page_url(data, url, 1)
        assert "startIndex=0" in next_url
        assert "stopIndex=100" in next_url

    def test_get_next_page_url_page_three(self, extractor):
        data = {"hasMoreItems": True}
        url = "https://www.homes.bg/api/offers?typeId=ApartmentSell"
        next_url = extractor.get_next_page_url(data, url, 3)
        assert "startIndex=200" in next_url
        assert "stopIndex=300" in next_url

    def test_determine_offer_type_house_sell(self, extractor):
        assert extractor._determine_offer_type({"typeId": "HouseSell"}) == "продава"

    def test_determine_offer_type_house_rent(self, extractor):
        assert extractor._determine_offer_type({"typeId": "HouseRent"}) == "наем"

    def test_extract_listing_with_all_fields(self, extractor):
        data = {
            "searchCriteria": {"typeId": "ApartmentSell"},
            "result": [
                {
                    "id": 99999,
                    "title": "Луксозен апартамент",
                    "description": "Описание",
                    "location": "Център, София",
                    "price": {"value": 500000, "currency": "EUR", "pricePerSquareMeter": "5000 EUR"},
                    "viewHref": "/offer/99999",
                    "photos": ["a.jpg", "b.jpg"],
                    "time": "2026-01-19",
                }
            ],
        }
        listings = list(extractor.extract_listings(data))
        assert len(listings) == 1
        assert "Луксозен апартамент" in listings[0].title
        assert "500000" in listings[0].price_text
        assert listings[0].num_photos == 2
        assert listings[0].ref_no == "99999"
