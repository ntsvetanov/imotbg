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
        assert result.price == 0.0

    def test_transform_listing_transform_error(self, parser):
        raw = {"raw_title": "Test", "price_text": "invalid"}
        result = parser.transform_listing(raw)

        assert result.raw_title == "Test"
        assert result.price is None

    def test_transform_listing_none_value(self, parser):
        raw = {"raw_title": None, "price_text": "100"}
        result = parser.transform_listing(raw)

        assert result.raw_title is None
        assert result.price == 100.0

    def test_transform_listing_model_dump(self, parser):
        raw = {"raw_title": "Test Title", "price_text": "100"}
        result = parser.transform_listing(raw).model_dump()

        assert isinstance(result, dict)
        assert result["site"] == "test"
        assert result["raw_title"] == "Test Title"
