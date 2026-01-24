"""Tests for the Reprocessor class."""

import math
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.reprocessor import Reprocessor, _clean_raw_record, reprocess_raw_data
from src.sites.suprimmo import SuprimmoParser


# =============================================================================
# _clean_raw_record Tests
# =============================================================================


class TestCleanRawRecord:
    def test_clean_nan_values(self):
        """NaN values should become None."""
        record = {"field1": float("nan"), "field2": "value"}
        result = _clean_raw_record(record)

        assert result["field1"] is None
        assert result["field2"] == "value"

    def test_clean_float_to_string(self):
        """Float values should be converted to strings."""
        record = {"price": 150000.0, "area": 65.5}
        result = _clean_raw_record(record)

        assert result["price"] == "150000.0"
        assert result["area"] == "65.5"

    def test_clean_preserves_strings(self):
        """String values should be preserved as-is."""
        record = {"title": "Test title", "city": "София"}
        result = _clean_raw_record(record)

        assert result["title"] == "Test title"
        assert result["city"] == "София"

    def test_clean_preserves_integers(self):
        """Integer values should be converted to strings."""
        record = {"count": 10, "page": 1}
        result = _clean_raw_record(record)

        # Integers are converted to strings for pydantic compatibility
        assert result["count"] == "10"
        assert result["page"] == "1"

    def test_clean_empty_record(self):
        """Empty record should return empty dict."""
        result = _clean_raw_record({})
        assert result == {}

    def test_clean_mixed_values(self):
        """Test mixed value types."""
        record = {
            "string": "test",
            "float": 123.45,
            "nan": float("nan"),
            "int": 100,
            "none": None,
        }
        result = _clean_raw_record(record)

        assert result["string"] == "test"
        assert result["float"] == "123.45"
        assert result["nan"] is None
        assert result["int"] == "100"  # Integers are converted to strings
        assert result["none"] is None


# =============================================================================
# Reprocessor Class Tests
# =============================================================================


class TestReprocessorInit:
    def test_init_with_parser(self):
        """Test initializing Reprocessor with a parser."""
        parser = SuprimmoParser()
        reprocessor = Reprocessor(parser)

        assert reprocessor.parser == parser
        assert reprocessor.site_name == "suprimmo"


class TestReprocessorReprocessFile:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    @pytest.fixture
    def reprocessor(self, parser):
        return Reprocessor(parser)

    def test_reprocess_file_success(self, reprocessor):
        """Test successful reprocessing of a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create raw file
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            raw_file = raw_dir / "test.csv"

            # Create sample raw data matching Suprimmo format
            raw_data = pd.DataFrame(
                [
                    {
                        "price_text": "150 000 EUR",
                        "title": "Тристаен апартамент",
                        "location": "гр. София / кв. Лозенец",
                        "area_text": "85 м",
                        "floor": "3",
                        "description": "Test description",
                        "details_url": "/prodajba-imot-sofia-12345.html",
                        "ref_no": "SOF 12345",
                        "offer_type": "продава",
                        "agency_name": "Test Agency",
                    }
                ]
            )
            raw_data.to_csv(raw_file, index=False)

            # Create output directory
            output_dir = Path(tmpdir) / "processed"

            # Reprocess
            result = reprocessor.reprocess_file(raw_file, output_dir)

            assert result is not None
            assert result.exists()
            assert result.name == "test.csv"

            # Verify content
            processed_df = pd.read_csv(result)
            assert len(processed_df) == 1
            assert processed_df.iloc[0]["site"] == "suprimmo"
            assert processed_df.iloc[0]["price"] == 150000.0

    def test_reprocess_file_empty(self, reprocessor):
        """Test reprocessing an empty file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_file = Path(tmpdir) / "empty.csv"
            # Create a file with headers but no data rows
            pd.DataFrame(columns=["price_text", "title", "location"]).to_csv(raw_file, index=False)

            output_dir = Path(tmpdir) / "output"
            result = reprocessor.reprocess_file(raw_file, output_dir)

            assert result is None

    def test_reprocess_file_new_mode(self, reprocessor):
        """Test reprocessing with 'new' output mode creates timestamped file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            raw_file = raw_dir / "test.csv"

            raw_data = pd.DataFrame(
                [
                    {
                        "price_text": "100 EUR",
                        "title": "Test",
                        "location": "София",
                        "area_text": "",
                        "floor": "",
                        "description": "",
                        "details_url": "/test.html",
                        "ref_no": "123",
                        "offer_type": "продава",
                        "agency_name": "",
                    }
                ]
            )
            raw_data.to_csv(raw_file, index=False)

            output_dir = Path(tmpdir) / "processed"
            result = reprocessor.reprocess_file(raw_file, output_dir, output_mode="new")

            assert result is not None
            assert "reprocessed" in result.name
            assert result.name != "test.csv"


class TestReprocessorReprocessFolder:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    @pytest.fixture
    def reprocessor(self, parser):
        return Reprocessor(parser)

    def test_reprocess_folder_success(self, reprocessor):
        """Test reprocessing a folder with multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory structure
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "sofia"
            raw_dir.mkdir(parents=True)

            # Create sample files
            for i in range(3):
                raw_data = pd.DataFrame(
                    [
                        {
                            "price_text": f"{100 + i * 50} EUR",
                            "title": f"Test {i}",
                            "location": "София",
                            "area_text": "",
                            "floor": "",
                            "description": "",
                            "details_url": f"/test{i}.html",
                            "ref_no": str(i),
                            "offer_type": "продава",
                            "agency_name": "",
                        }
                    ]
                )
                raw_data.to_csv(raw_dir / f"file{i}.csv", index=False)

            results = reprocessor.reprocess_folder("sofia", base_path=tmpdir)

            assert len(results) == 3

    def test_reprocess_folder_not_found(self, reprocessor):
        """Test returns empty list when folder doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = reprocessor.reprocess_folder("nonexistent", base_path=tmpdir)
            assert results == []

    def test_reprocess_folder_no_csv_files(self, reprocessor):
        """Test returns empty list when no CSV files in folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "empty"
            raw_dir.mkdir(parents=True)

            results = reprocessor.reprocess_folder("empty", base_path=tmpdir)
            assert results == []


class TestReprocessorReprocessSite:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    @pytest.fixture
    def reprocessor(self, parser):
        return Reprocessor(parser)

    def test_reprocess_site_success(self, reprocessor):
        """Test reprocessing entire site."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple folders
            for folder in ["sofia", "plovdiv"]:
                raw_dir = Path(tmpdir) / "raw" / "suprimmo" / folder
                raw_dir.mkdir(parents=True)
                raw_data = pd.DataFrame(
                    [
                        {
                            "price_text": "100 EUR",
                            "title": "Test",
                            "location": folder,
                            "area_text": "",
                            "floor": "",
                            "description": "",
                            "details_url": f"/{folder}.html",
                            "ref_no": "1",
                            "offer_type": "продава",
                            "agency_name": "",
                        }
                    ]
                )
                raw_data.to_csv(raw_dir / "data.csv", index=False)

            results = reprocessor.reprocess_site(base_path=tmpdir)

            assert len(results) == 2

    def test_reprocess_site_not_found(self, reprocessor):
        """Test returns empty list when site directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = reprocessor.reprocess_site(base_path=tmpdir)
            assert results == []


# =============================================================================
# reprocess_raw_data Function Tests
# =============================================================================


class TestReprocessRawDataFunction:
    def test_invalid_output_mode(self):
        """Test raises error for invalid output mode."""
        with pytest.raises(ValueError) as exc_info:
            reprocess_raw_data("Suprimmo", output_mode="invalid")

        assert "Invalid output_mode" in str(exc_info.value)

    def test_reprocess_entire_site(self):
        """Test reprocessing entire site via function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
            raw_data = pd.DataFrame(
                [
                    {
                        "price_text": "100 EUR",
                        "title": "Test",
                        "location": "София",
                        "area_text": "",
                        "floor": "",
                        "description": "",
                        "details_url": "/test.html",
                        "ref_no": "1",
                        "offer_type": "продава",
                        "agency_name": "",
                    }
                ]
            )
            raw_data.to_csv(raw_dir / "data.csv", index=False)

            results = reprocess_raw_data("Suprimmo", base_path=tmpdir)

            assert len(results) == 1

    def test_reprocess_single_file(self):
        """Test reprocessing a single file via function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "data.csv"
            raw_data = pd.DataFrame(
                [
                    {
                        "price_text": "100 EUR",
                        "title": "Test",
                        "location": "София",
                        "area_text": "",
                        "floor": "",
                        "description": "",
                        "details_url": "/test.html",
                        "ref_no": "1",
                        "offer_type": "продава",
                        "agency_name": "",
                    }
                ]
            )
            raw_data.to_csv(raw_file, index=False)

            results = reprocess_raw_data("Suprimmo", path=str(raw_file), base_path=tmpdir)

            assert len(results) == 1

    def test_reprocess_folder_via_function(self):
        """Test reprocessing a folder via function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "sofia"
            raw_dir.mkdir(parents=True)
            raw_data = pd.DataFrame(
                [
                    {
                        "price_text": "100 EUR",
                        "title": "Test",
                        "location": "София",
                        "area_text": "",
                        "floor": "",
                        "description": "",
                        "details_url": "/test.html",
                        "ref_no": "1",
                        "offer_type": "продава",
                        "agency_name": "",
                    }
                ]
            )
            raw_data.to_csv(raw_dir / "data.csv", index=False)

            results = reprocess_raw_data("Suprimmo", path="sofia", base_path=tmpdir)

            assert len(results) == 1

    def test_reprocess_with_new_mode(self):
        """Test reprocessing with new output mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
            raw_data = pd.DataFrame(
                [
                    {
                        "price_text": "100 EUR",
                        "title": "Test",
                        "location": "София",
                        "area_text": "",
                        "floor": "",
                        "description": "",
                        "details_url": "/test.html",
                        "ref_no": "1",
                        "offer_type": "продава",
                        "agency_name": "",
                    }
                ]
            )
            raw_data.to_csv(raw_dir / "data.csv", index=False)

            results = reprocess_raw_data("Suprimmo", base_path=tmpdir, output_mode="new")

            assert len(results) == 1
            # New mode creates timestamped files
            assert "reprocessed" in results[0].name
