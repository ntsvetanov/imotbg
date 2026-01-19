import json
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from main import load_url_config, run_site_scraper


class TestRunSiteScraper:
    @pytest.fixture
    def mock_scraper(self):
        with patch("main.GenericScraper") as mock:
            scraper_instance = MagicMock()
            scraper_instance.scrape.return_value = {
                "raw_df": pd.DataFrame([{"title": "Test"}]),
                "processed_df": pd.DataFrame([{"title": "Test", "price": 100}]),
            }
            scraper_instance.save_results.return_value = True
            mock.return_value = scraper_instance
            yield mock, scraper_instance

    @pytest.fixture
    def mock_get_parser(self):
        with patch("main.get_parser") as mock:
            parser = MagicMock()
            mock.return_value = parser
            yield mock, parser

    def test_run_site_scraper_success(self, mock_scraper, mock_get_parser):
        _, scraper_instance = mock_scraper
        urls = [{"url": "http://test.com/1"}, {"url": "http://test.com/2"}]

        result = run_site_scraper("ImotBg", urls, "results")

        assert len(result) == 2
        assert scraper_instance.scrape.call_count == 2
        assert scraper_instance.save_results.call_count == 2

    def test_run_site_scraper_empty_urls(self, mock_scraper, mock_get_parser):
        result = run_site_scraper("ImotBg", [], "results")

        assert len(result) == 0

    def test_run_site_scraper_handles_exception(self, mock_scraper, mock_get_parser):
        _, scraper_instance = mock_scraper
        scraper_instance.scrape.side_effect = Exception("Network error")
        urls = [{"url": "http://test.com/1"}]

        result = run_site_scraper("ImotBg", urls, "results")

        assert len(result) == 0

    def test_run_site_scraper_no_data(self, mock_scraper, mock_get_parser):
        _, scraper_instance = mock_scraper
        scraper_instance.save_results.return_value = False
        urls = [{"url": "http://test.com/1"}]

        result = run_site_scraper("ImotBg", urls, "results")

        assert len(result) == 0

    def test_run_site_scraper_sends_email_on_failure(self, mock_scraper, mock_get_parser):
        _, scraper_instance = mock_scraper
        scraper_instance.save_results.return_value = False
        urls = [{"url": "http://test.com/1"}]
        email_client = MagicMock()

        run_site_scraper("ImotBg", urls, "results", email_client=email_client)

        email_client.send_email.assert_called_once()
        call_args = email_client.send_email.call_args
        assert "No data for ImotBg" in call_args.kwargs["subject"]
        assert "http://test.com/1" in call_args.kwargs["text"]

    def test_run_site_scraper_no_email_on_success(self, mock_scraper, mock_get_parser):
        urls = [{"url": "http://test.com/1"}]
        email_client = MagicMock()

        run_site_scraper("ImotBg", urls, "results", email_client=email_client)

        email_client.send_email.assert_not_called()

    def test_run_site_scraper_partial_success(self, mock_scraper, mock_get_parser):
        _, scraper_instance = mock_scraper
        scraper_instance.save_results.side_effect = [True, False]
        urls = [{"url": "http://test.com/1"}, {"url": "http://test.com/2"}]

        result = run_site_scraper("ImotBg", urls, "results")

        assert len(result) == 1


class TestLoadUrlConfig:
    def test_load_url_config(self):
        config = {"ImotBg": {"urls": [{"url": "http://test.com"}]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()

            with patch("main.open", return_value=open(f.name)):
                with patch("builtins.open", return_value=open(f.name)):
                    pass

    def test_load_url_config_file_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "value"}, f)
            temp_path = f.name

        with patch("builtins.open", return_value=open(temp_path)):
            result = load_url_config()
            assert result == {"test": "value"}


class TestMainIntegration:
    @patch("main.load_url_config")
    @patch("main.get_parser")
    @patch("main.run_site_scraper")
    def test_main_runs_all_sites(self, mock_run, mock_get_parser, mock_load_config):
        mock_load_config.return_value = {
            "ImotBg": {"urls": [{"url": "http://imot.bg"}]},
            "ImotiNet": {"urls": [{"url": "http://imoti.net"}]},
            "HomesBg": {"neighborhoods": [{"id": 1}]},
        }

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = ["http://test.com"]
        mock_get_parser.return_value = mock_parser

        mock_run.return_value = pd.DataFrame()

        with patch("sys.argv", ["main.py", "--scraper_name", "all"]):
            from main import main

            main()

        assert mock_run.call_count == 4

    @patch("main.load_url_config")
    @patch("main.get_parser")
    @patch("main.run_site_scraper")
    def test_main_runs_single_site(self, mock_run, mock_get_parser, mock_load_config):
        mock_load_config.return_value = {"ImotBg": {"urls": [{"url": "http://imot.bg"}]}}

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = ["http://test.com"]
        mock_get_parser.return_value = mock_parser

        mock_run.return_value = pd.DataFrame()

        with patch("sys.argv", ["main.py", "--scraper_name", "ImotBg"]):
            from main import main

            main()

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "ImotBg"

    @patch("main.load_url_config")
    @patch("main.get_parser")
    @patch("main.run_site_scraper")
    def test_main_skips_site_without_urls(self, mock_run, mock_get_parser, mock_load_config):
        mock_load_config.return_value = {"ImotBg": {}}

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = []
        mock_get_parser.return_value = mock_parser

        with patch("sys.argv", ["main.py", "--scraper_name", "ImotBg"]):
            from main import main

            main()

        mock_run.assert_not_called()

    @patch("main.load_url_config")
    @patch("main.get_parser")
    @patch("main.run_site_scraper")
    def test_main_custom_result_folder(self, mock_run, mock_get_parser, mock_load_config):
        mock_load_config.return_value = {"ImotBg": {"urls": [{"url": "http://imot.bg"}]}}

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = ["http://test.com"]
        mock_get_parser.return_value = mock_parser

        mock_run.return_value = pd.DataFrame()

        with patch("sys.argv", ["main.py", "--scraper_name", "ImotBg", "--result_folder", "custom_results"]):
            from main import main

            main()

        assert mock_run.call_args[0][2] == "custom_results"

    @patch("main.scrape_single_url")
    def test_main_with_url_bypasses_config(self, mock_scrape):
        mock_scrape.return_value = pd.DataFrame([{"price": 100, "city": "Sofia"}])

        with patch("sys.argv", ["main.py", "--scraper_name", "ImotBg", "--url", "http://direct-url.com"]):
            from main import main

            main()

        mock_scrape.assert_called_once_with("ImotBg", "http://direct-url.com")

    def test_main_url_requires_scraper_name(self):
        with patch("sys.argv", ["main.py", "--url", "http://direct-url.com"]):
            from main import main

            with pytest.raises(SystemExit):
                main()
