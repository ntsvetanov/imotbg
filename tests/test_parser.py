import pytest
from bs4 import BeautifulSoup

from src.core.models import ListingData
from src.core.parser import BaseParser, Field, SiteConfig


class TestField:
    def test_field_with_transform(self):
        field = Field("source_key", lambda x: x.upper())
        assert field.source == "source_key"
        assert field.transform("test") == "TEST"

    def test_field_without_transform(self):
        field = Field("source_key", None)
        assert field.source == "source_key"
        assert field.transform is None

    def test_field_default_transform(self):
        field = Field("source_key")
        assert field.transform is None


class TestSiteConfig:
    def test_site_config_defaults(self):
        config = SiteConfig(name="test", base_url="https://test.com")
        assert config.name == "test"
        assert config.base_url == "https://test.com"
        assert config.encoding == "utf-8"
        assert config.source_type == "html"
        assert config.rate_limit_seconds == 1.0

    def test_site_config_custom_values(self):
        config = SiteConfig(
            name="test",
            base_url="https://test.com",
            encoding="windows-1251",
            source_type="json",
            rate_limit_seconds=2.5,
        )
        assert config.encoding == "windows-1251"
        assert config.source_type == "json"
        assert config.rate_limit_seconds == 2.5


class ConcreteParser(BaseParser):
    config = SiteConfig(name="test", base_url="https://test.com")

    class Fields:
        raw_title = Field("raw_title", None)
        price = Field("price_text", lambda x: float(x.replace(" ", "")))

    @staticmethod
    def build_urls(config: dict) -> list[str]:
        return config.get("urls", [])

    def extract_listings(self, content):
        yield {"raw_title": "Test", "price_text": "100"}

    def get_next_page_url(self, content, current_url: str, page_number: int):
        return None


class TestBaseParser:
    @pytest.fixture
    def parser(self):
        return ConcreteParser()

    @pytest.fixture
    def sample_html(self):
        return BeautifulSoup(
            """
            <div class="listing">
                <h1 class="title">Test Title</h1>
                <a href="/details/123" class="link">Link</a>
                <span data-value="42">Value</span>
            </div>
            """,
            "html.parser",
        )

    def test_get_text(self, parser, sample_html):
        assert parser.get_text("h1.title", sample_html) == "Test Title"

    def test_get_text_not_found(self, parser, sample_html):
        assert parser.get_text("h2.missing", sample_html) == ""

    def test_get_text_custom_default(self, parser, sample_html):
        assert parser.get_text("h2.missing", sample_html, "default") == "default"

    def test_get_href(self, parser, sample_html):
        assert parser.get_href("a.link", sample_html) == "/details/123"

    def test_get_href_not_found(self, parser, sample_html):
        assert parser.get_href("a.missing", sample_html) is None

    def test_get_attr(self, parser, sample_html):
        assert parser.get_attr("span", "data-value", sample_html) == "42"

    def test_get_attr_not_found(self, parser, sample_html):
        assert parser.get_attr("span.missing", "data-value", sample_html) is None

    def test_get_json_value(self, parser):
        data = {"level1": {"level2": {"value": 42}}}
        assert parser.get_json_value(data, "level1.level2.value") == 42

    def test_get_json_value_not_found(self, parser):
        data = {"level1": {"level2": {"value": 42}}}
        assert parser.get_json_value(data, "level1.missing.value") is None

    def test_get_json_value_default(self, parser):
        data = {"level1": {}}
        assert parser.get_json_value(data, "level1.missing", "default") == "default"

    def test_get_total_pages_default(self, parser, sample_html):
        assert parser.get_total_pages(sample_html) == 100

    def test_build_urls(self):
        config = {"urls": ["http://a.com", "http://b.com"]}
        assert ConcreteParser.build_urls(config) == ["http://a.com", "http://b.com"]

    def test_build_urls_empty(self):
        assert ConcreteParser.build_urls({}) == []


class TestTransformListing:
    @pytest.fixture
    def parser(self):
        return ConcreteParser()

    def test_transform_listing_returns_listing_data(self, parser):
        raw = {"raw_title": "Test Title", "price_text": "100"}
        result = parser.transform_listing(raw)

        assert isinstance(result, ListingData)

    def test_transform_listing_basic(self, parser):
        raw = {"raw_title": "Test Title", "price_text": "100"}
        result = parser.transform_listing(raw)

        assert result.site == "test"
        assert result.raw_title == "Test Title"
        assert result.price == 100.0

    def test_transform_listing_missing_field(self, parser):
        raw = {"raw_title": "Test Title"}
        result = parser.transform_listing(raw)

        assert result.raw_title == "Test Title"
        assert result.price is None  # default from model (no price_text in raw)

    def test_transform_listing_transform_error(self, parser):
        raw = {"raw_title": "Test", "price_text": "invalid"}
        result = parser.transform_listing(raw)

        assert result.raw_title == "Test"
        assert result.price is None  # default from model (transform failed)

    def test_transform_listing_none_value(self, parser):
        raw = {"raw_title": None, "price_text": "100"}
        result = parser.transform_listing(raw)

        assert result.raw_title == ""  # default from model (None input)
        assert result.price == 100.0

    def test_transform_listing_model_dump(self, parser):
        raw = {"raw_title": "Test Title", "price_text": "100"}
        result = parser.transform_listing(raw).model_dump()

        assert isinstance(result, dict)
        assert result["site"] == "test"
        assert result["raw_title"] == "Test Title"


class TestFieldWithPrependUrl:
    def test_field_prepend_url_true(self):
        field = Field("url", prepend_url=True)
        assert field.source == "url"
        assert field.prepend_url is True
        assert field.transform is None

    def test_field_prepend_url_default(self):
        field = Field("url")
        assert field.prepend_url is False


class TestSiteConfigAdvanced:
    def test_site_config_max_pages_default(self):
        config = SiteConfig(name="test", base_url="https://test.com")
        assert config.max_pages == 100

    def test_site_config_page_size_default(self):
        config = SiteConfig(name="test", base_url="https://test.com")
        assert config.page_size == 100

    def test_site_config_all_custom(self):
        config = SiteConfig(
            name="custom",
            base_url="https://custom.com",
            encoding="iso-8859-1",
            source_type="api",
            rate_limit_seconds=3.0,
            max_pages=50,
            page_size=25,
        )
        assert config.max_pages == 50
        assert config.page_size == 25


class TestBaseParserPrependUrl:
    @pytest.fixture
    def parser(self):
        return ConcreteParser()

    def test_prepend_base_url_empty(self, parser):
        assert parser._prepend_base_url("") == ""

    def test_prepend_base_url_http(self, parser):
        assert parser._prepend_base_url("http://other.com/path") == "http://other.com/path"

    def test_prepend_base_url_https(self, parser):
        assert parser._prepend_base_url("https://other.com/path") == "https://other.com/path"

    def test_prepend_base_url_protocol_relative(self, parser):
        assert parser._prepend_base_url("//www.example.com/path") == "https://www.example.com/path"

    def test_prepend_base_url_relative(self, parser):
        assert parser._prepend_base_url("/some/path") == "https://test.com/some/path"


class TestBaseParserGetJsonValue:
    @pytest.fixture
    def parser(self):
        return ConcreteParser()

    def test_get_json_value_nested(self, parser):
        data = {"a": {"b": {"c": 42}}}
        assert parser.get_json_value(data, "a.b.c") == 42

    def test_get_json_value_list_in_path(self, parser):
        data = {"a": [1, 2, 3]}
        # Lists aren't dicts, so this should return default
        assert parser.get_json_value(data, "a.0") is None

    def test_get_json_value_empty_dict(self, parser):
        data = {}
        assert parser.get_json_value(data, "a.b.c") is None

    def test_get_json_value_partial_path(self, parser):
        data = {"a": {"b": 42}}
        assert parser.get_json_value(data, "a.b") == 42

    def test_get_json_value_single_level(self, parser):
        data = {"key": "value"}
        assert parser.get_json_value(data, "key") == "value"


class TestBaseParserEdgeCases:
    @pytest.fixture
    def parser(self):
        return ConcreteParser()

    def test_get_text_with_whitespace(self, parser):
        html = BeautifulSoup("<div class='test'>  Text with spaces  </div>", "html.parser")
        assert parser.get_text("div.test", html) == "Text with spaces"

    def test_get_href_empty_href(self, parser):
        html = BeautifulSoup('<a href="" class="link">Link</a>', "html.parser")
        assert parser.get_href("a.link", html) == ""

    def test_get_attr_missing_attribute(self, parser):
        html = BeautifulSoup('<span class="test">Text</span>', "html.parser")
        assert parser.get_attr("span.test", "data-missing", html) is None

    def test_transform_listing_field_not_in_raw(self, parser):
        raw = {}  # Empty dict
        result = parser.transform_listing(raw)
        assert result.raw_title == ""  # default from model
        assert result.price is None  # default from model

    def test_extract_listings_generator(self, parser):
        listings = parser.extract_listings({})
        # Should be a generator
        import types

        assert isinstance(listings, types.GeneratorType)


class TestConcreteParserWithPrependUrl:
    def test_transform_with_prepend_url(self):
        class ParserWithUrl(BaseParser):
            config = SiteConfig(name="urltest", base_url="https://example.com")

            class Fields:
                details_url = Field("link_path", prepend_url=True)
                raw_title = Field("title")

            @staticmethod
            def build_urls(config: dict):
                return []

            def extract_listings(self, content):
                yield {}

            def get_next_page_url(self, content, url, page):
                return None

        parser = ParserWithUrl()
        raw = {"link_path": "/details/123", "title": "Test"}
        result = parser.transform_listing(raw)

        assert result.details_url == "https://example.com/details/123"

    def test_transform_with_prepend_url_empty(self):
        class ParserWithUrl(BaseParser):
            config = SiteConfig(name="urltest", base_url="https://example.com")

            class Fields:
                details_url = Field("link_path", prepend_url=True)

            @staticmethod
            def build_urls(config: dict):
                return []

            def extract_listings(self, content):
                yield {}

            def get_next_page_url(self, content, url, page):
                return None

        parser = ParserWithUrl()
        raw = {"link_path": ""}
        result = parser.transform_listing(raw)

        # Empty string should not be prepended
        assert result.details_url == ""
