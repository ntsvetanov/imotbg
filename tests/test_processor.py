import math
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.core.processor import Processor, clean_raw_record
from src.sites.suprimmo import SuprimmoParser


class TestCleanRawRecord:
    def test_nan_values_become_none(self):
        record = {"field1": float("nan"), "field2": "value"}
        result = clean_raw_record(record)

        assert result["field1"] is None
        assert result["field2"] == "value"

    def test_float_to_string(self):
        record = {"price": 150000.0, "area": 65.5}
        result = clean_raw_record(record)

        assert result["price"] == "150000.0"
        assert result["area"] == "65.5"

    def test_preserves_strings(self):
        record = {"title": "Test title", "city": "София"}
        result = clean_raw_record(record)

        assert result["title"] == "Test title"
        assert result["city"] == "София"

    def test_int_to_string(self):
        record = {"count": 10, "page": 1}
        result = clean_raw_record(record)

        assert result["count"] == "10"
        assert result["page"] == "1"

    def test_empty_record(self):
        result = clean_raw_record({})
        assert result == {}

    def test_mixed_values(self):
        record = {
            "string": "test",
            "float": 123.45,
            "nan": float("nan"),
            "int": 100,
            "none": None,
        }
        result = clean_raw_record(record)

        assert result["string"] == "test"
        assert result["float"] == "123.45"
        assert result["nan"] is None
        assert result["int"] == "100"
        assert result["none"] is None


class TestProcessorInit:
    def test_init_with_parser(self):
        parser = SuprimmoParser()
        processor = Processor(parser)

        assert processor.parser == parser
        assert processor.site_name == "suprimmo"


class TestProcessorProcessFile:
    @pytest.fixture
    def parser(self):
        return SuprimmoParser()

    @pytest.fixture
    def processor(self, parser):
        return Processor(parser)

    def test_process_file_success(self, processor):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "test.csv"

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

            processor = Processor(SuprimmoParser(), tmpdir)
            result = processor.process_file(raw_file)

            assert result is not None
            assert result.exists()
            assert result.name == "test.csv"

            processed_df = pd.read_csv(result)
            assert len(processed_df) == 1
            assert processed_df.iloc[0]["site"] == "suprimmo"
            assert processed_df.iloc[0]["price"] == 150000.0

    def test_process_file_empty(self, processor):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "empty.csv"
            pd.DataFrame(columns=["price_text", "title", "location"]).to_csv(raw_file, index=False)

            processor = Processor(SuprimmoParser(), tmpdir)
            result = processor.process_file(raw_file)

            assert result is None


class TestProcessorGetUnprocessedFiles:
    def test_finds_unprocessed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)

            processed_dir = Path(tmpdir) / "processed" / "suprimmo" / "test"
            processed_dir.mkdir(parents=True)

            # Create 3 raw files
            for i in range(3):
                pd.DataFrame([{"title": f"Test {i}"}]).to_csv(raw_dir / f"file{i}.csv", index=False)

            # Create 1 processed file (file1.csv)
            pd.DataFrame([{"title": "Test 1"}]).to_csv(processed_dir / "file1.csv", index=False)

            processor = Processor(SuprimmoParser(), tmpdir)
            unprocessed = processor.get_unprocessed_files()

            assert len(unprocessed) == 2
            names = [f.name for f in unprocessed]
            assert "file0.csv" in names
            assert "file2.csv" in names
            assert "file1.csv" not in names

    def test_returns_empty_when_no_raw_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = Processor(SuprimmoParser(), tmpdir)
            unprocessed = processor.get_unprocessed_files()

            assert unprocessed == []


class TestProcessorReprocessFile:
    def test_reprocess_overwrite_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
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

            processor = Processor(SuprimmoParser(), tmpdir)
            result = processor.reprocess_file(raw_file, output_mode="overwrite")

            assert result is not None
            assert result.name == "test.csv"

    def test_reprocess_new_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "test"
            raw_dir.mkdir(parents=True)
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

            processor = Processor(SuprimmoParser(), tmpdir)
            result = processor.reprocess_file(raw_file, output_mode="new")

            assert result is not None
            assert "reprocessed" in result.name
            assert result.name != "test.csv"


class TestProcessorReprocessFolder:
    def test_reprocess_folder_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "suprimmo" / "sofia"
            raw_dir.mkdir(parents=True)

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

            processor = Processor(SuprimmoParser(), tmpdir)
            results = processor.reprocess_folder("sofia")

            assert len(results) == 3

    def test_reprocess_folder_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = Processor(SuprimmoParser(), tmpdir)
            results = processor.reprocess_folder("nonexistent")
            assert results == []


class TestProcessorReprocessAll:
    def test_reprocess_all_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
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

            processor = Processor(SuprimmoParser(), tmpdir)
            results = processor.reprocess_all()

            assert len(results) == 2

    def test_reprocess_all_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = Processor(SuprimmoParser(), tmpdir)
            results = processor.reprocess_all()
            assert results == []
