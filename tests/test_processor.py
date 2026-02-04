import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.core.processor import Processor
from src.sites.suprimmo import SuprimmoExtractor


class TestProcessorInit:
    def test_init_with_extractor(self):
        extractor = SuprimmoExtractor()
        processor = Processor(extractor)

        assert processor.extractor == extractor
        assert processor.site_name == "suprimmo"


class TestProcessorProcessFile:
    @pytest.fixture
    def extractor(self):
        return SuprimmoExtractor()

    @pytest.fixture
    def processor(self, extractor):
        return Processor(extractor)

    def test_process_file_success(self, extractor):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use year_month_override to control the directory structure
            year_month = "2026/01"
            raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "test.csv"

            raw_data = pd.DataFrame(
                [
                    {
                        "site": "suprimmo",
                        "scraped_at": "2026-01-15T10:30:00",
                        "price_text": "150 000 €",
                        "title": "продава Тристаен апартамент",
                        "location_text": "гр. София / кв. Лозенец",
                        "area_text": "85 м",
                        "floor_text": "3 ет.",
                        "details_url": "https://www.suprimmo.bg/prodajba-imot-sofia-12345.html",
                        "ref_no": "SOF 12345",
                        "agency_name": "Test Agency",
                        "num_photos": 5,
                        "total_offers": 100,
                    }
                ]
            )
            raw_data.to_csv(raw_file, index=False)

            processor = Processor(extractor, tmpdir, year_month_override=year_month)
            result = processor.process_file(raw_file)

            assert result is not None
            assert result.exists()
            assert result.name == "test.csv"

            processed_df = pd.read_csv(result)
            assert len(processed_df) == 1
            assert processed_df.iloc[0]["site"] == "suprimmo"
            assert processed_df.iloc[0]["price"] == 150000.0

    def test_process_file_empty(self, extractor):
        with tempfile.TemporaryDirectory() as tmpdir:
            year_month = "2026/01"
            raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "empty.csv"
            pd.DataFrame(columns=["price_text", "title", "location_text"]).to_csv(raw_file, index=False)

            processor = Processor(extractor, tmpdir, year_month_override=year_month)
            result = processor.process_file(raw_file)

            assert result is None


class TestProcessorGetUnprocessedFiles:
    def test_finds_unprocessed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            year_month = "2026/01"
            raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo"
            raw_dir.mkdir(parents=True)

            processed_dir = Path(tmpdir) / year_month / "processed" / "suprimmo"
            processed_dir.mkdir(parents=True)

            # Create 3 raw files
            for i in range(3):
                pd.DataFrame([{"title": f"Test {i}"}]).to_csv(raw_dir / f"file{i}.csv", index=False)

            # Create 1 processed file (file1.csv)
            pd.DataFrame([{"title": "Test 1"}]).to_csv(processed_dir / "file1.csv", index=False)

            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override=year_month)
            unprocessed = processor.get_unprocessed_files()

            assert len(unprocessed) == 2
            names = [f.name for f in unprocessed]
            assert "file0.csv" in names
            assert "file2.csv" in names
            assert "file1.csv" not in names

    def test_returns_empty_when_no_raw_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override="2026/01")
            unprocessed = processor.get_unprocessed_files()

            assert unprocessed == []


class TestProcessorReprocessFile:
    def test_reprocess_overwrite_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            year_month = "2026/01"
            raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "test.csv"

            raw_data = pd.DataFrame(
                [
                    {
                        "site": "suprimmo",
                        "scraped_at": "2026-01-15T10:30:00",
                        "price_text": "100 €",
                        "title": "продава Test",
                        "location_text": "София",
                        "area_text": "",
                        "floor_text": "",
                        "details_url": "https://www.suprimmo.bg/test.html",
                        "ref_no": "REF123",
                        "agency_name": "",
                        "num_photos": 0,
                        "total_offers": 0,
                    }
                ]
            )
            raw_data.to_csv(raw_file, index=False)

            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override=year_month)
            result = processor.reprocess_file(raw_file, output_mode="overwrite")

            assert result is not None
            assert result.name == "test.csv"

    def test_reprocess_new_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            year_month = "2026/01"
            raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "test.csv"

            raw_data = pd.DataFrame(
                [
                    {
                        "site": "suprimmo",
                        "scraped_at": "2026-01-15T10:30:00",
                        "price_text": "100 €",
                        "title": "продава Test",
                        "location_text": "София",
                        "area_text": "",
                        "floor_text": "",
                        "details_url": "https://www.suprimmo.bg/test.html",
                        "ref_no": "REF123",
                        "agency_name": "",
                        "num_photos": 0,
                        "total_offers": 0,
                    }
                ]
            )
            raw_data.to_csv(raw_file, index=False)

            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override=year_month)
            result = processor.reprocess_file(raw_file, output_mode="new")

            assert result is not None
            assert "reprocessed" in result.name
            assert result.name != "test.csv"


class TestProcessorReprocessFolder:
    def test_reprocess_folder_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            year_month = "2026/01"
            raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo" / "sofia"
            raw_dir.mkdir(parents=True)

            for i in range(3):
                raw_data = pd.DataFrame(
                    [
                        {
                            "site": "suprimmo",
                            "scraped_at": "2026-01-15T10:30:00",
                            "price_text": f"{100 + i * 50} €",
                            "title": f"продава Test {i}",
                            "location_text": "София",
                            "area_text": "",
                            "floor_text": "",
                            "details_url": f"https://www.suprimmo.bg/test{i}.html",
                            "ref_no": f"REF{i}",
                            "agency_name": "",
                            "num_photos": 0,
                            "total_offers": 0,
                        }
                    ]
                )
                raw_data.to_csv(raw_dir / f"file{i}.csv", index=False)

            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override=year_month)
            results = processor.reprocess_folder("sofia")

            assert len(results) == 3

    def test_reprocess_folder_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override="2026/01")
            results = processor.reprocess_folder("nonexistent")
            assert results == []


class TestProcessorReprocessAll:
    def test_reprocess_all_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            year_month = "2026/01"
            for idx, folder in enumerate(["sofia", "plovdiv"]):
                raw_dir = Path(tmpdir) / year_month / "raw" / "suprimmo" / folder
                raw_dir.mkdir(parents=True)
                raw_data = pd.DataFrame(
                    [
                        {
                            "site": "suprimmo",
                            "scraped_at": "2026-01-15T10:30:00",
                            "price_text": "100 €",
                            "title": "продава Test",
                            "location_text": folder,
                            "area_text": "",
                            "floor_text": "",
                            "details_url": f"https://www.suprimmo.bg/{folder}.html",
                            "ref_no": f"REF{idx}",
                            "agency_name": "",
                            "num_photos": 0,
                            "total_offers": 0,
                        }
                    ]
                )
                raw_data.to_csv(raw_dir / "data.csv", index=False)

            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override=year_month)
            results = processor.reprocess_all()

            assert len(results) == 2

    def test_reprocess_all_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = Processor(SuprimmoExtractor(), tmpdir, year_month_override="2026/01")
            results = processor.reprocess_all()
            assert results == []
