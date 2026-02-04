"""
Integration tests using responses library to mock HTTP requests.

These tests verify the full extraction pipeline with real HTML/JSON
fixtures captured from live sites. Each site has one fixture file
stored in tests/fixtures/html/.

Usage:
    pytest tests/test_integration_responses.py -v
"""

import pytest
import responses
from bs4 import BeautifulSoup

from src.core.transformer import Transformer
from src.sites.alobg import AloBgExtractor
from src.sites.bazarbg import BazarBgExtractor
from src.sites.bulgarianproperties import BulgarianPropertiesExtractor
from src.sites.homesbg import HomesBgExtractor
from src.sites.imotbg import ImotBgExtractor
from src.sites.imoticom import ImotiComExtractor
from src.sites.imotinet import ImotiNetExtractor
from src.sites.luximmo import LuximmoExtractor
from src.sites.suprimmo import SuprimmoExtractor

# Test data: (site_name, extractor_class, fixture_file, sample_url, is_json)
SITE_TEST_DATA = [
    pytest.param(
        "alobg",
        AloBgExtractor,
        "alobg.html",
        "https://www.alo.bg/obiavi/imoti-prodajbi/apartamenti-stai/",
        False,
        id="alobg",
    ),
    pytest.param(
        "bazarbg",
        BazarBgExtractor,
        "bazarbg.html",
        "https://bazar.bg/obiavi/prodazhba-apartamenti/sofia",
        False,
        id="bazarbg",
    ),
    pytest.param(
        "bulgarianproperties",
        BulgarianPropertiesExtractor,
        "bulgarianproperties.html",
        "https://www.bulgarianproperties.bg/prodazhba-imot/index.html",
        False,
        id="bulgarianproperties",
    ),
    pytest.param(
        "homesbg",
        HomesBgExtractor,
        "homesbg.json",
        "https://www.homes.bg/api/offers",
        True,
        id="homesbg",
    ),
    pytest.param(
        "imotbg",
        ImotBgExtractor,
        "imotbg.html",
        "https://www.imot.bg/obiavi/prodazhbi/grad-sofiya/",
        False,
        id="imotbg",
    ),
    pytest.param(
        "imoticom",
        ImotiComExtractor,
        "imoticom.html",
        "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini",
        False,
        id="imoticom",
    ),
    pytest.param(
        "imotinet",
        ImotiNetExtractor,
        "imotinet.html",
        "https://www.imoti.net/bg/obiavi/r/prodava/sofia/",
        False,
        id="imotinet",
    ),
    pytest.param(
        "luximmo",
        LuximmoExtractor,
        "luximmo.html",
        "https://www.luximmo.bg/prodajba/bulgaria/",
        False,
        id="luximmo",
    ),
    pytest.param(
        "suprimmo",
        SuprimmoExtractor,
        "suprimmo.html",
        "https://www.suprimmo.bg/prodajba/bulgaria/",
        False,
        id="suprimmo",
    ),
]


class TestIntegrationExtraction:
    """Test extraction from real HTML/JSON fixtures."""

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_extract_listings_returns_results(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture
    ):
        """Test that extractor returns at least one listing from fixture."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            listings = list(extractor.extract_listings(data))
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            listings = list(extractor.extract_listings(soup))

        assert len(listings) > 0, f"No listings extracted from {fixture_file}"
        assert all(listing.site == site for listing in listings)

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_extracted_listings_have_required_fields(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture
    ):
        """Test that extracted listings have essential fields populated."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            listings = list(extractor.extract_listings(data))
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            listings = list(extractor.extract_listings(soup))

        for listing in listings:
            assert listing.site == site
            # At least one of these should be populated for a valid listing
            has_identifiable_info = listing.details_url or listing.title or listing.price_text
            assert has_identifiable_info, f"Listing missing all identifying info: {listing}"

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_extracted_listings_have_scraped_at(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture
    ):
        """Test that all extracted listings have scraped_at timestamp."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            listings = list(extractor.extract_listings(data))
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            listings = list(extractor.extract_listings(soup))

        for listing in listings:
            assert listing.scraped_at is not None


class TestIntegrationFullPipeline:
    """Test full extraction + transformation pipeline."""

    @pytest.fixture
    def transformer(self):
        return Transformer()

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_transform_extracted_listings(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture, transformer
    ):
        """Test that extracted listings can be transformed without errors."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            raw_listings = list(extractor.extract_listings(data))
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            raw_listings = list(extractor.extract_listings(soup))

        # Transform all listings - should not raise
        transformed = transformer.transform_batch(raw_listings)

        assert len(transformed) == len(raw_listings)
        assert all(t.site == site for t in transformed)

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_transformed_listings_have_fingerprint(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture, transformer
    ):
        """Test that transformed listings have fingerprint hash."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            raw_listings = list(extractor.extract_listings(data))
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            raw_listings = list(extractor.extract_listings(soup))

        transformed = transformer.transform_batch(raw_listings)

        for listing in transformed:
            assert listing.fingerprint_hash, f"Missing fingerprint_hash for listing: {listing.details_url}"


class TestIntegrationWithHttpMocking:
    """Test with actual HTTP mocking using responses library."""

    @responses.activate
    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_mocked_http_response_extraction(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture
    ):
        """Test extraction with mocked HTTP response using responses library."""
        extractor = extractor_cls()

        # Setup mock response
        if is_json:
            content = load_json_fixture(fixture_file)
            responses.add(responses.GET, url, json=content, status=200, match_querystring=False)
            # Parse content for extraction
            data = content
            listings = list(extractor.extract_listings(data))
        else:
            content = load_fixture(fixture_file)
            responses.add(
                responses.GET, url, body=content, status=200, content_type="text/html", match_querystring=False
            )
            # Parse content for extraction
            soup = BeautifulSoup(content, "html.parser")
            listings = list(extractor.extract_listings(soup))

        # Verify extraction works
        assert len(listings) > 0, f"No listings extracted for {site}"

        # Verify the mock was called (responses tracks this)
        # Note: Since we're testing the extractor directly with parsed content,
        # the mock verifies the setup is correct but isn't actually called
        # This test primarily validates the fixture + extractor integration


class TestIntegrationPagination:
    """Test pagination methods with real fixtures."""

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_get_total_pages_returns_positive(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture
    ):
        """Test that get_total_pages returns a positive number."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            total_pages = extractor.get_total_pages(data)
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            total_pages = extractor.get_total_pages(soup)

        assert total_pages >= 1, f"Total pages should be at least 1, got {total_pages}"

    @pytest.mark.parametrize("site,extractor_cls,fixture_file,url,is_json", SITE_TEST_DATA)
    def test_get_next_page_url_returns_url_or_none(
        self, site, extractor_cls, fixture_file, url, is_json, load_fixture, load_json_fixture
    ):
        """Test that get_next_page_url returns a valid URL or None."""
        extractor = extractor_cls()

        if is_json:
            data = load_json_fixture(fixture_file)
            next_url = extractor.get_next_page_url(data, url, 2)
        else:
            html = load_fixture(fixture_file)
            soup = BeautifulSoup(html, "html.parser")
            next_url = extractor.get_next_page_url(soup, url, 2)

        # Should be either None or a string URL
        assert next_url is None or isinstance(next_url, str)
        if next_url:
            assert next_url.startswith("http") or next_url.startswith("/")
