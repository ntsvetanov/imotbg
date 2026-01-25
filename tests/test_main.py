import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from main import download_site, load_url_config, process_site, reprocess_site


class TestDownloadSite:
    @patch("main.Downloader")
    @patch("main.get_parser")
    @patch("main.load_url_config")
    def test_download_site_success(self, mock_load_config, mock_get_parser, mock_downloader_class):
        mock_load_config.return_value = {"TestSite": {"urls": [{"url": "http://test.com"}]}}

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = [{"url": "http://test.com", "folder": "test"}]
        mock_get_parser.return_value = mock_parser

        mock_downloader = MagicMock()
        mock_downloader.download.return_value = Path("/tmp/test.csv")
        mock_downloader_class.return_value = mock_downloader

        result = download_site("TestSite", "results")

        assert result == 1
        mock_downloader.download.assert_called_once_with("http://test.com", "test", 0)

    @patch("main.Downloader")
    @patch("main.get_parser")
    @patch("main.load_url_config")
    def test_download_site_no_urls(self, mock_load_config, mock_get_parser, mock_downloader_class):
        mock_load_config.return_value = {"TestSite": {}}

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = []
        mock_get_parser.return_value = mock_parser

        result = download_site("TestSite", "results")

        assert result == 0

    @patch("main.Downloader")
    @patch("main.get_parser")
    @patch("main.load_url_config")
    def test_download_site_handles_exception(self, mock_load_config, mock_get_parser, mock_downloader_class):
        mock_load_config.return_value = {"TestSite": {}}

        mock_parser = MagicMock()
        mock_parser.build_urls.return_value = [{"url": "http://test.com"}]
        mock_get_parser.return_value = mock_parser

        mock_downloader = MagicMock()
        mock_downloader.download.side_effect = Exception("Network error")
        mock_downloader_class.return_value = mock_downloader

        result = download_site("TestSite", "results")

        assert result == 0


class TestProcessSite:
    @patch("main.Processor")
    @patch("main.get_parser")
    def test_process_site_all_unprocessed(self, mock_get_parser, mock_processor_class):
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        mock_processor = MagicMock()
        mock_processor.process_all_unprocessed.return_value = [Path("/tmp/a.csv"), Path("/tmp/b.csv")]
        mock_processor_class.return_value = mock_processor

        result = process_site("TestSite", "results")

        assert result == 2
        mock_processor.process_all_unprocessed.assert_called_once()

    @patch("main.Processor")
    @patch("main.get_parser")
    def test_process_site_single_file(self, mock_get_parser, mock_processor_class):
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        mock_processor = MagicMock()
        mock_processor.process_file.return_value = Path("/tmp/output.csv")
        mock_processor_class.return_value = mock_processor

        result = process_site("TestSite", "results", file_path="/tmp/input.csv")

        assert result == 1
        mock_processor.process_file.assert_called_once_with(Path("/tmp/input.csv"))


class TestReprocessSite:
    @patch("main.Processor")
    @patch("main.get_parser")
    def test_reprocess_site_all(self, mock_get_parser, mock_processor_class):
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        mock_processor = MagicMock()
        mock_processor.reprocess_all.return_value = [Path("/tmp/a.csv")]
        mock_processor_class.return_value = mock_processor

        result = reprocess_site("TestSite", "results")

        assert result == 1
        mock_processor.reprocess_all.assert_called_once_with("overwrite")

    @patch("main.Processor")
    @patch("main.get_parser")
    def test_reprocess_site_folder(self, mock_get_parser, mock_processor_class):
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        mock_processor = MagicMock()
        mock_processor.reprocess_folder.return_value = [Path("/tmp/a.csv")]
        mock_processor_class.return_value = mock_processor

        result = reprocess_site("TestSite", "results", folder="sofia")

        assert result == 1
        mock_processor.reprocess_folder.assert_called_once_with("sofia", "overwrite")

    @patch("main.Processor")
    @patch("main.get_parser")
    def test_reprocess_site_single_file(self, mock_get_parser, mock_processor_class):
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        mock_processor = MagicMock()
        mock_processor.reprocess_file.return_value = Path("/tmp/output.csv")
        mock_processor_class.return_value = mock_processor

        result = reprocess_site("TestSite", "results", file_path="/tmp/input.csv")

        assert result == 1
        mock_processor.reprocess_file.assert_called_once_with(Path("/tmp/input.csv"), "overwrite")

    @patch("main.Processor")
    @patch("main.get_parser")
    def test_reprocess_site_new_mode(self, mock_get_parser, mock_processor_class):
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        mock_processor = MagicMock()
        mock_processor.reprocess_all.return_value = []
        mock_processor_class.return_value = mock_processor

        reprocess_site("TestSite", "results", output_mode="new")

        mock_processor.reprocess_all.assert_called_once_with("new")


class TestLoadUrlConfig:
    def test_load_url_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "value"}, f)
            temp_path = f.name

        with patch("builtins.open", return_value=open(temp_path)):
            result = load_url_config()
            assert result == {"test": "value"}


class TestMainIntegration:
    @patch("main.download_site")
    @patch("main.process_site")
    def test_main_scrape_calls_download_and_process(self, mock_process, mock_download):
        mock_download.return_value = 1
        mock_process.return_value = 1

        with patch("sys.argv", ["main.py", "scrape", "--site", "TestSite"]):
            from main import main

            main()

        mock_download.assert_called_once_with("TestSite", "results")
        mock_process.assert_called_once_with("TestSite", "results")

    @patch("main.download_site")
    def test_main_download_only(self, mock_download):
        mock_download.return_value = 1

        with patch("sys.argv", ["main.py", "download", "--site", "TestSite"]):
            from main import main

            main()

        mock_download.assert_called_once_with("TestSite", "results")

    @patch("main.process_site")
    def test_main_process_only(self, mock_process):
        mock_process.return_value = 1

        with patch("sys.argv", ["main.py", "process", "--site", "TestSite"]):
            from main import main

            main()

        mock_process.assert_called_once_with("TestSite", "results", None)

    @patch("main.reprocess_site")
    def test_main_reprocess(self, mock_reprocess):
        mock_reprocess.return_value = 1

        with patch("sys.argv", ["main.py", "reprocess", "--site", "TestSite", "--folder", "sofia"]):
            from main import main

            main()

        mock_reprocess.assert_called_once_with(
            "TestSite",
            "results",
            folder="sofia",
            file_path=None,
            output_mode="overwrite",
        )

    @patch("main.download_site")
    @patch("main.process_site")
    def test_main_custom_result_folder(self, mock_process, mock_download):
        mock_download.return_value = 1
        mock_process.return_value = 1

        with patch("sys.argv", ["main.py", "scrape", "--site", "TestSite", "--result_folder", "custom"]):
            from main import main

            main()

        mock_download.assert_called_once_with("TestSite", "custom")
        mock_process.assert_called_once_with("TestSite", "custom")
