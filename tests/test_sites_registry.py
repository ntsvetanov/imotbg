import pytest

from src.sites import SITE_EXTRACTORS, get_extractor
from src.sites.bazarbg import BazarBgExtractor
from src.sites.homesbg import HomesBgExtractor
from src.sites.imotbg import ImotBgExtractor
from src.sites.imoticom import ImotiComExtractor
from src.sites.imotinet import ImotiNetExtractor


class TestSiteExtractorsRegistry:
    def test_registry_contains_bazarbg(self):
        assert "BazarBg" in SITE_EXTRACTORS
        assert SITE_EXTRACTORS["BazarBg"] == BazarBgExtractor

    def test_registry_contains_imotbg(self):
        assert "ImotBg" in SITE_EXTRACTORS
        assert SITE_EXTRACTORS["ImotBg"] == ImotBgExtractor

    def test_registry_contains_imotinet(self):
        assert "ImotiNet" in SITE_EXTRACTORS
        assert SITE_EXTRACTORS["ImotiNet"] == ImotiNetExtractor

    def test_registry_contains_homesbg(self):
        assert "HomesBg" in SITE_EXTRACTORS
        assert SITE_EXTRACTORS["HomesBg"] == HomesBgExtractor

    def test_registry_contains_imoticom(self):
        assert "ImotiCom" in SITE_EXTRACTORS
        assert SITE_EXTRACTORS["ImotiCom"] == ImotiComExtractor

    def test_registry_has_all_extractors(self):
        expected_extractors = {
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
        assert set(SITE_EXTRACTORS.keys()) == expected_extractors


class TestGetExtractor:
    def test_get_extractor_bazarbg(self):
        extractor = get_extractor("BazarBg")
        assert isinstance(extractor, BazarBgExtractor)

    def test_get_extractor_imotbg(self):
        extractor = get_extractor("ImotBg")
        assert isinstance(extractor, ImotBgExtractor)

    def test_get_extractor_imotinet(self):
        extractor = get_extractor("ImotiNet")
        assert isinstance(extractor, ImotiNetExtractor)

    def test_get_extractor_homesbg(self):
        extractor = get_extractor("HomesBg")
        assert isinstance(extractor, HomesBgExtractor)

    def test_get_extractor_imoticom(self):
        extractor = get_extractor("ImotiCom")
        assert isinstance(extractor, ImotiComExtractor)

    def test_get_extractor_unknown_site(self):
        with pytest.raises(ValueError) as exc_info:
            get_extractor("UnknownSite")
        assert "Unknown site: UnknownSite" in str(exc_info.value)

    def test_get_extractor_returns_new_instance(self):
        extractor1 = get_extractor("ImotBg")
        extractor2 = get_extractor("ImotBg")
        assert extractor1 is not extractor2
