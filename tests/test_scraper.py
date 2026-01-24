from unittest.mock import patch

import pandas as pd
import pytest

from src.core.parser import BaseParser, Field, SiteConfig
from src.core.scraper import GenericScraper


class MockParser(BaseParser):
    config = SiteConfig(name="mocksite", base_url="https://mock.com")

    class Fields:
        title = Field("title", None)
        price = Field("price", float)

    @staticmethod
    def build_urls(config: dict) -> list[str]:
        return config.get("urls", [])

    def extract_listings(self, content):
        for item in content.get("items", []):
            yield item

    def get_next_page_url(self, content, current_url: str, page_number: int):
        if page_number <= content.get("total_pages", 1):
            return f"{current_url}?page={page_number}"
        return None

    def get_total_pages(self, content):
        return content.get("total_pages", 1)


class TestGenericScraperInit:
    def test_init_default_folder(self):
        parser = MockParser()
        scraper = GenericScraper(parser)

        assert scraper.parser == parser
        assert scraper.config == parser.config
        assert scraper.result_folder == "results"
        assert scraper.timestamp is not None

    def test_init_custom_folder(self):
        parser = MockParser()
        scraper = GenericScraper(parser, result_folder="custom_results")

        assert scraper.result_folder == "custom_results"


class TestGenericScraperFetchContent:
    @pytest.fixture
    def scraper(self):
        return GenericScraper(MockParser())

    def test_fetch_content_json(self, scraper):
        scraper.config = SiteConfig(name="test", base_url="https://test.com", source_type="json")

        with patch.object(scraper.http_client, "fetch_json") as mock_fetch:
            mock_fetch.return_value = {"data": "test"}
            result = scraper.fetch_content("https://test.com/api")

            mock_fetch.assert_called_once_with("https://test.com/api")
            assert result == {"data": "test"}

    def test_fetch_content_html(self, scraper):
        with patch.object(scraper.http_client, "fetch") as mock_fetch:
            mock_fetch.return_value = "<html><body>Test</body></html>"
            result = scraper.fetch_content("https://test.com/page")

            mock_fetch.assert_called_once_with("https://test.com/page", "utf-8")
            assert result is not None


class TestGenericScraperScrape:
    @pytest.fixture
    def scraper(self):
        parser = MockParser()
        scraper = GenericScraper(parser)
        return scraper

    def test_scrape_single_page(self, scraper):
        mock_content = {
            "items": [
                {"title": "Item 1", "price": "100"},
                {"title": "Item 2", "price": "200"},
            ],
            "total_pages": 1,
        }

        with patch.object(scraper, "fetch_content", return_value=mock_content):
            result = scraper.scrape("https://test.com/listings")

            assert "raw_df" in result
            assert "processed_df" in result
            assert len(result["raw_df"]) == 2
            assert len(result["processed_df"]) == 2

    def test_scrape_multiple_pages(self, scraper):
        page1_content = {
            "items": [{"title": "Item 1", "price": "100"}],
            "total_pages": 2,
        }
        page2_content = {
            "items": [{"title": "Item 2", "price": "200"}],
            "total_pages": 2,
        }

        call_count = [0]

        def mock_fetch(url):
            call_count[0] += 1
            return page1_content if call_count[0] == 1 else page2_content

        with patch.object(scraper, "fetch_content", side_effect=mock_fetch):
            with patch("time.sleep"):
                result = scraper.scrape("https://test.com/listings")

                assert len(result["raw_df"]) == 2

    def test_scrape_adds_metadata(self, scraper):
        mock_content = {
            "items": [{"title": "Item 1", "price": "100"}],
            "total_pages": 1,
        }

        with patch.object(scraper, "fetch_content", return_value=mock_content):
            result = scraper.scrape("https://test.com/listings")

            raw_df = result["raw_df"]
            assert "search_url" in raw_df.columns
            assert "scraped_at" in raw_df.columns
            assert raw_df["search_url"].iloc[0] == "https://test.com/listings"

    def test_scrape_empty_listings(self, scraper):
        mock_content = {"items": [], "total_pages": 1}

        with patch.object(scraper, "fetch_content", return_value=mock_content):
            result = scraper.scrape("https://test.com/listings")

            assert len(result["raw_df"]) == 0
            assert len(result["processed_df"]) == 0


class TestGenericScraperSaveResults:
    @pytest.fixture
    def scraper(self):
        return GenericScraper(MockParser(), result_folder="test_results")

    def test_save_results_success(self, scraper):
        raw_df = pd.DataFrame([{"title": "Test", "price": 100}])
        processed_df = pd.DataFrame([{"title": "Test", "price": 100.0}])

        with patch("src.core.scraper.save_df_to_csv") as mock_save:
            mock_save.return_value = True
            result = scraper.save_results(raw_df, processed_df, 0)

            assert result is True
            assert mock_save.call_count == 2

    def test_save_results_empty_df(self, scraper):
        raw_df = pd.DataFrame()
        processed_df = pd.DataFrame()

        with patch("src.core.scraper.save_df_to_csv") as mock_save:
            mock_save.return_value = False
            result = scraper.save_results(raw_df, processed_df, 0)

            assert result is False
            mock_save.assert_called_once()

    def test_save_results_correct_paths(self, scraper):
        raw_df = pd.DataFrame([{"title": "Test"}])
        processed_df = pd.DataFrame([{"title": "Test"}])

        with patch("src.core.scraper.save_df_to_csv") as mock_save:
            mock_save.return_value = True
            scraper.save_results(raw_df, processed_df, 0)

            calls = mock_save.call_args_list
            assert "test_results/raw/mocksite" in calls[0][0][1]
            assert "test_results/processed/mocksite" in calls[1][0][1]

    def test_save_results_with_folder(self, scraper):
        raw_df = pd.DataFrame([{"title": "Test"}])
        processed_df = pd.DataFrame([{"title": "Test"}])

        with patch("src.core.scraper.save_df_to_csv") as mock_save:
            mock_save.return_value = True
            scraper.save_results(raw_df, processed_df, 0, folder="subfolder")

            calls = mock_save.call_args_list
            assert "test_results/raw/mocksite/subfolder" in calls[0][0][1]
            assert "test_results/processed/mocksite/subfolder" in calls[1][0][1]


class TestGenericScraperEdgeCases:
    @pytest.fixture
    def scraper(self):
        return GenericScraper(MockParser())

    def test_scrape_stops_when_exceeds_total_pages(self, scraper):
        mock_content = {
            "items": [{"title": "Item 1", "price": "100"}],
            "total_pages": 1,
        }

        with patch.object(scraper, "fetch_content", return_value=mock_content):
            with patch("time.sleep"):
                result = scraper.scrape("https://test.com/listings")

                assert len(result["raw_df"]) == 1

    def test_scrape_stops_when_no_next_page(self, scraper):
        content1 = {
            "items": [{"title": "Item 1", "price": "100"}],
            "total_pages": 5,
        }
        content2 = {
            "items": [],
            "total_pages": 5,
        }

        call_count = [0]

        def mock_fetch(url):
            call_count[0] += 1
            return content1 if call_count[0] == 1 else content2

        with patch.object(scraper, "fetch_content", side_effect=mock_fetch):
            with patch("time.sleep"):
                # Need to modify parser behavior for this test
                scraper.parser.get_next_page_url = lambda c, u, p: None if not c.get("items") else f"{u}?page={p}"
                result = scraper.scrape("https://test.com/listings")

                assert len(result["raw_df"]) == 1

    def test_scrape_respects_rate_limit(self, scraper):
        mock_content = {
            "items": [{"title": "Item 1", "price": "100"}],
            "total_pages": 2,
        }

        with patch.object(scraper, "fetch_content", return_value=mock_content):
            with patch("time.sleep") as mock_sleep:
                scraper.scrape("https://test.com/listings")

                assert mock_sleep.call_count >= 1
                mock_sleep.assert_called_with(scraper.config.rate_limit_seconds)

    def test_fetch_content_html_with_custom_encoding(self, scraper):
        scraper.config.encoding = "windows-1251"

        with patch.object(scraper.http_client, "fetch") as mock_fetch:
            mock_fetch.return_value = "<html><body>Test</body></html>"
            scraper.fetch_content("https://test.com/page")

            mock_fetch.assert_called_once_with("https://test.com/page", "windows-1251")

    def test_scrape_processed_df_structure(self, scraper):
        mock_content = {
            "items": [{"title": "Item 1", "price": "100"}],
            "total_pages": 1,
        }

        with patch.object(scraper, "fetch_content", return_value=mock_content):
            result = scraper.scrape("https://test.com/listings")

            # Verify both dataframes have the same length
            assert len(result["raw_df"]) == len(result["processed_df"])

    def test_scrape_url_index_with_different_values(self, scraper):
        raw_df = pd.DataFrame([{"title": "Test"}])
        processed_df = pd.DataFrame([{"title": "Test"}])

        with patch("src.core.scraper.save_df_to_csv") as mock_save:
            mock_save.return_value = True

            scraper.save_results(raw_df, processed_df, 5)

            calls = mock_save.call_args_list
            # Verify url_index is passed correctly
            assert calls[0][0][3] == 5
            assert calls[1][0][3] == 5

    def test_timestamp_format(self, scraper):
        import re

        # Timestamp should be in format YYYY_MM_DD_HH_MM_SS
        pattern = r"^\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$"
        assert re.match(pattern, scraper.timestamp)
