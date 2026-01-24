import pytest

from src.sites import SITE_PARSERS, get_parser
from src.sites.bazarbg import BazarBgParser
from src.sites.homesbg import HomesBgParser
from src.sites.imotbg import ImotBgParser
from src.sites.imoticom import ImotiComParser
from src.sites.imotinet import ImotiNetParser


class TestSiteParsersRegistry:
    def test_registry_contains_bazarbg(self):
        assert "BazarBg" in SITE_PARSERS
        assert SITE_PARSERS["BazarBg"] == BazarBgParser

    def test_registry_contains_imotbg(self):
        assert "ImotBg" in SITE_PARSERS
        assert SITE_PARSERS["ImotBg"] == ImotBgParser

    def test_registry_contains_imotinet(self):
        assert "ImotiNet" in SITE_PARSERS
        assert SITE_PARSERS["ImotiNet"] == ImotiNetParser

    def test_registry_contains_homesbg(self):
        assert "HomesBg" in SITE_PARSERS
        assert SITE_PARSERS["HomesBg"] == HomesBgParser

    def test_registry_contains_imoticom(self):
        assert "ImotiCom" in SITE_PARSERS
        assert SITE_PARSERS["ImotiCom"] == ImotiComParser

    def test_registry_has_all_parsers(self):
        expected_parsers = {
            "AloBg",
            "BazarBg",
            "BulgarianProperties",
            "HomesBg",
            "ImotiCom",
            "ImotBg",
            "ImotiNet",
            "ImotiNetPlovdiv",
            "Luximmo",
            "Suprimmo",
        }
        assert set(SITE_PARSERS.keys()) == expected_parsers


class TestGetParser:
    def test_get_parser_bazarbg(self):
        parser = get_parser("BazarBg")
        assert isinstance(parser, BazarBgParser)

    def test_get_parser_imotbg(self):
        parser = get_parser("ImotBg")
        assert isinstance(parser, ImotBgParser)

    def test_get_parser_imotinet(self):
        parser = get_parser("ImotiNet")
        assert isinstance(parser, ImotiNetParser)

    def test_get_parser_homesbg(self):
        parser = get_parser("HomesBg")
        assert isinstance(parser, HomesBgParser)

    def test_get_parser_imoticom(self):
        parser = get_parser("ImotiCom")
        assert isinstance(parser, ImotiComParser)

    def test_get_parser_unknown_site(self):
        with pytest.raises(ValueError) as exc_info:
            get_parser("UnknownSite")
        assert "Unknown site: UnknownSite" in str(exc_info.value)

    def test_get_parser_returns_new_instance(self):
        parser1 = get_parser("ImotBg")
        parser2 = get_parser("ImotBg")
        assert parser1 is not parser2
