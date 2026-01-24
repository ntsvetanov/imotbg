import pytest

from src.infrastructure.clients.browser_profiles import (
    BROWSER_PROFILES,
    get_random_profile,
    get_profile_by_browser,
)


class TestBrowserProfiles:
    def test_profiles_exist(self):
        assert len(BROWSER_PROFILES) >= 5

    def test_all_profiles_have_required_headers(self):
        required_headers = [
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Accept-Encoding",
            "Sec-Fetch-Dest",
            "Sec-Fetch-Mode",
            "Connection",
        ]
        for profile in BROWSER_PROFILES:
            for header in required_headers:
                assert header in profile, f"Profile missing {header}"

    def test_chrome_profiles_have_client_hints(self):
        chrome_profiles = [
            p for p in BROWSER_PROFILES if "Chrome" in p["User-Agent"] and "Firefox" not in p["User-Agent"]
        ]
        assert len(chrome_profiles) >= 1
        for profile in chrome_profiles:
            assert profile.get("Sec-CH-UA") is not None
            assert profile.get("Sec-CH-UA-Mobile") is not None
            assert profile.get("Sec-CH-UA-Platform") is not None

    def test_firefox_profiles_no_client_hints(self):
        firefox_profiles = [p for p in BROWSER_PROFILES if "Firefox" in p["User-Agent"]]
        assert len(firefox_profiles) >= 1
        for profile in firefox_profiles:
            assert profile.get("Sec-CH-UA") is None
            assert profile.get("Sec-CH-UA-Mobile") is None
            assert profile.get("Sec-CH-UA-Platform") is None


class TestGetRandomProfile:
    def test_returns_dict(self):
        profile = get_random_profile()
        assert isinstance(profile, dict)

    def test_no_none_values(self):
        """Returned profile should not contain None values."""
        for _ in range(20):  # Run multiple times due to randomness
            profile = get_random_profile()
            assert all(v is not None for v in profile.values())

    def test_has_user_agent(self):
        profile = get_random_profile()
        assert "User-Agent" in profile
        assert len(profile["User-Agent"]) > 0


class TestGetProfileByBrowser:
    def test_get_chrome_profile(self):
        profile = get_profile_by_browser("chrome")
        assert "Chrome" in profile["User-Agent"]
        assert "Edg" not in profile["User-Agent"]

    def test_get_firefox_profile(self):
        profile = get_profile_by_browser("firefox")
        assert "Firefox" in profile["User-Agent"]
        # Firefox profiles should not have Sec-CH-UA headers
        assert "Sec-CH-UA" not in profile

    def test_get_edge_profile(self):
        profile = get_profile_by_browser("edge")
        assert "Edg" in profile["User-Agent"]

    def test_case_insensitive(self):
        profile_lower = get_profile_by_browser("chrome")
        profile_upper = get_profile_by_browser("CHROME")
        profile_mixed = get_profile_by_browser("Chrome")
        assert "Chrome" in profile_lower["User-Agent"]
        assert "Chrome" in profile_upper["User-Agent"]
        assert "Chrome" in profile_mixed["User-Agent"]

    def test_unknown_browser_raises(self):
        with pytest.raises(ValueError, match="Unknown browser"):
            get_profile_by_browser("safari")
