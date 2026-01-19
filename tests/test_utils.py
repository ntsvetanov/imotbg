import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from src.utils import get_now_date, get_now_for_filename, parse_soup, save_df_to_csv


class TestParseSoup:
    def test_parse_soup_valid_html(self):
        html = "<html><body><h1>Test</h1></body></html>"
        soup = parse_soup(html)

        assert isinstance(soup, BeautifulSoup)
        assert soup.h1.text == "Test"

    def test_parse_soup_empty_string(self):
        with pytest.raises(ValueError) as exc_info:
            parse_soup("")
        assert "Page content cannot be empty" in str(exc_info.value)

    def test_parse_soup_none(self):
        with pytest.raises(ValueError):
            parse_soup(None)


class TestGetNowForFilename:
    def test_get_now_for_filename_format(self):
        result = get_now_for_filename()

        assert len(result) == 19
        assert result.count("_") == 5
        parts = result.split("_")
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2
        assert len(parts[2]) == 2

    @patch("src.utils.datetime")
    def test_get_now_for_filename_specific_date(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 45)
        result = get_now_for_filename()

        assert result == "2024_01_15_10_30_45"


class TestGetNowDate:
    def test_get_now_date_format(self):
        result = get_now_date()

        assert len(result) == 10
        assert result.count("-") == 2

    @patch("src.utils.datetime")
    def test_get_now_date_specific_date(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 45)
        result = get_now_date()

        assert result == "2024-01-15"


class TestSaveDfToCsv:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

    @pytest.fixture
    def empty_df(self):
        return pd.DataFrame()

    def test_save_df_creates_directory(self, sample_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "new_folder")
            result = save_df_to_csv(sample_df, path, "2024_01_15", 0)

            assert result is True
            assert os.path.exists(path)

    def test_save_df_creates_file(self, sample_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_df_to_csv(sample_df, tmpdir, "2024_01_15", 0)

            expected_file = os.path.join(tmpdir, "2024_01_15_0.csv")
            assert os.path.exists(expected_file)

    def test_save_df_file_content(self, sample_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_df_to_csv(sample_df, tmpdir, "2024_01_15", 0)

            file_path = os.path.join(tmpdir, "2024_01_15_0.csv")
            loaded_df = pd.read_csv(file_path)

            assert len(loaded_df) == 3
            assert list(loaded_df.columns) == ["col1", "col2"]

    def test_save_df_returns_true_on_success(self, sample_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_df_to_csv(sample_df, tmpdir, "2024_01_15", 0)
            assert result is True

    def test_save_df_returns_false_on_empty(self, empty_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_df_to_csv(empty_df, tmpdir, "2024_01_15", 0)
            assert result is False

    def test_save_df_empty_does_not_create_file(self, empty_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_df_to_csv(empty_df, tmpdir, "2024_01_15", 0)

            expected_file = os.path.join(tmpdir, "2024_01_15_0.csv")
            assert not os.path.exists(expected_file)

    def test_save_df_url_idx_in_filename(self, sample_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_df_to_csv(sample_df, tmpdir, "2024_01_15", 5)

            expected_file = os.path.join(tmpdir, "2024_01_15_5.csv")
            assert os.path.exists(expected_file)
