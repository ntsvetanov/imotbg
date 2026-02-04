"""Shared pytest fixtures for integration tests."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


@pytest.fixture
def load_fixture():
    """Load HTML/JSON fixture by filename.

    Usage:
        def test_something(load_fixture):
            html = load_fixture("alobg.html")
    """

    def _load(filename: str) -> str:
        filepath = FIXTURES_DIR / filename
        if not filepath.exists():
            pytest.skip(f"Fixture not found: {filepath}")
        return filepath.read_text(encoding="utf-8")

    return _load


@pytest.fixture
def load_json_fixture():
    """Load and parse JSON fixture by filename.

    Usage:
        def test_something(load_json_fixture):
            data = load_json_fixture("homesbg.json")
    """

    def _load(filename: str) -> dict:
        filepath = FIXTURES_DIR / filename
        if not filepath.exists():
            pytest.skip(f"Fixture not found: {filepath}")
        return json.loads(filepath.read_text(encoding="utf-8"))

    return _load
