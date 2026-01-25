import gzip
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.downloader import Downloader
from src.core.parser import BaseParser, Field, SiteConfig


class MockParser(BaseParser):
    config = SiteConfig(name="mocksite", base_url="https://mock.com")

    class Fields:
        title = Field("title", None)
        price = Field("price", float)

    def extract_listings(self, content):
        for item in content.get("items", []):
            yield item

    def get_next_page_url(self, content, current_url: str, page_number: int):
        if page_number <= content.get("total_pages", 1):
            return f"{current_url}?page={page_number}"
        return None

    def get_total_pages(self, content):
        return content.get("total_pages", 1)


class TestDownloaderInit:
    def test_init_default_folder(self):
        parser = MockParser()
        downloader = Downloader(parser)

        assert downloader.parser == parser
        assert downloader.config == parser.config
        assert downloader.result_folder == "results"
        assert downloader.timestamp is not None

    def test_init_custom_folder(self):
        parser = MockParser()
        downloader = Downloader(parser, result_folder="custom_results")

        assert downloader.result_folder == "custom_results"

    def test_init_uses_cloudscraper_when_configured(self):
        parser = MockParser()
        parser.config = SiteConfig(name="test", base_url="https://test.com", use_cloudscraper=True)

        with patch("src.core.downloader.CloudscraperHttpClient") as mock_cloudscraper:
            Downloader(parser)
            mock_cloudscraper.assert_called_once()

    def test_init_uses_http_client_by_default(self):
        parser = MockParser()

        with patch("src.core.downloader.HttpClient") as mock_http:
            Downloader(parser)
            mock_http.assert_called_once()


class TestDownloaderDownload:
    @pytest.fixture
    def downloader(self):
        parser = MockParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = Downloader(parser, result_folder=tmpdir)
            yield downloader

    def test_download_single_page(self, downloader):
        mock_content = {
            "items": [
                {"title": "Item 1", "price": "100"},
                {"title": "Item 2", "price": "200"},
            ],
            "total_pages": 1,
        }

        with patch.object(downloader, "_fetch_with_raw", return_value=("{}", mock_content)):
            with patch("time.sleep"):
                result = downloader.download("https://test.com/listings")

                assert result is not None
                assert result.exists()
                assert result.suffix == ".csv"

                df = pd.read_csv(result)
                assert len(df) == 2
                assert "search_url" in df.columns
                assert "scraped_at" in df.columns

    def test_download_multiple_pages(self, downloader):
        page1 = {"items": [{"title": "Item 1", "price": "100"}], "total_pages": 2}
        page2 = {"items": [{"title": "Item 2", "price": "200"}], "total_pages": 2}

        call_count = [0]

        def mock_fetch(url):
            call_count[0] += 1
            return ("{}", page1 if call_count[0] == 1 else page2)

        with patch.object(downloader, "_fetch_with_raw", side_effect=mock_fetch):
            with patch("time.sleep"):
                result = downloader.download("https://test.com/listings")

                df = pd.read_csv(result)
                assert len(df) == 2

    def test_download_saves_fallback_on_empty(self, downloader):
        mock_content = {"items": [], "total_pages": 1}

        with patch.object(downloader, "_fetch_with_raw", return_value=("<html></html>", mock_content)):
            with patch("time.sleep"):
                result = downloader.download("https://test.com/listings")

                assert result is None

                fallback_dir = Path(downloader.result_folder) / "raw_html" / "mocksite"
                fallback_files = list(fallback_dir.glob("*.html.gz"))
                assert len(fallback_files) == 1

    def test_download_with_folder(self, downloader):
        mock_content = {"items": [{"title": "Item 1", "price": "100"}], "total_pages": 1}

        with patch.object(downloader, "_fetch_with_raw", return_value=("{}", mock_content)):
            with patch("time.sleep"):
                result = downloader.download("https://test.com/listings", folder="sofia/apartments", url_index=0)

                assert "sofia" in str(result)
                assert "apartments" in str(result)


class TestDownloaderSaveFallback:
    def test_save_fallback_creates_gzip(self):
        parser = MockParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = Downloader(parser, result_folder=tmpdir)
            html_content = "<html><body>Test</body></html>"

            result = downloader._save_fallback(html_content, None, 0)

            assert result.exists()
            assert result.suffix == ".gz"

            with gzip.open(result, "rt", encoding="utf-8") as f:
                content = f.read()
                assert content == html_content

    def test_save_fallback_json_extension(self):
        parser = MockParser()
        parser.config = SiteConfig(name="test", base_url="https://test.com", source_type="json")

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = Downloader(parser, result_folder=tmpdir)

            result = downloader._save_fallback('{"data": "test"}', None, 0)

            assert ".json.gz" in str(result)


class TestDownloaderFetchWithRaw:
    def test_fetch_html_returns_tuple(self):
        parser = MockParser()
        downloader = Downloader(parser)

        with patch.object(downloader.http_client, "fetch", return_value="<html><body>Test</body></html>"):
            raw, parsed = downloader._fetch_with_raw("https://test.com")

            assert raw == "<html><body>Test</body></html>"
            assert parsed is not None

    def test_fetch_json_returns_tuple(self):
        parser = MockParser()
        parser.config = SiteConfig(name="test", base_url="https://test.com", source_type="json")
        downloader = Downloader(parser)

        with patch.object(downloader.http_client, "fetch_json", return_value={"data": "test"}):
            raw, parsed = downloader._fetch_with_raw("https://test.com")

            assert '"data": "test"' in raw
            assert parsed == {"data": "test"}


class TestDownloaderTimestamp:
    def test_timestamp_format(self):
        import re

        parser = MockParser()
        downloader = Downloader(parser)

        pattern = r"^\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$"
        assert re.match(pattern, downloader.timestamp)
