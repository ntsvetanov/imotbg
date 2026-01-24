"""
Browser profiles for realistic HTTP request headers.

Each profile simulates a real browser fingerprint including:
- User-Agent string
- Sec-CH-UA client hints (Chromium-based browsers)
- Sec-Fetch metadata headers
- Accept headers

Usage:
    from browser_profiles import get_random_profile
    headers = get_random_profile()
"""

import random
from typing import TypedDict


class BrowserProfile(TypedDict):
    User_Agent: str
    Accept: str
    Accept_Language: str
    Accept_Encoding: str
    Sec_CH_UA: str | None
    Sec_CH_UA_Mobile: str
    Sec_CH_UA_Platform: str | None
    Sec_Fetch_Dest: str
    Sec_Fetch_Mode: str
    Sec_Fetch_Site: str
    Sec_Fetch_User: str
    Upgrade_Insecure_Requests: str
    Connection: str
    Cache_Control: str


# Modern browser profiles with realistic headers (as of late 2024/early 2025)
BROWSER_PROFILES: list[dict[str, str | None]] = [
    # Chrome 131 on Windows 10
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    },
    # Chrome 131 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    },
    # Edge 131 on Windows 10
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-CH-UA": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    },
    # Firefox 133 on Windows 10 (no Sec-CH-UA - Firefox doesn't support client hints)
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
        "Accept-Language": "bg,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-CH-UA": None,  # Firefox doesn't send client hints
        "Sec-CH-UA-Mobile": None,
        "Sec-CH-UA-Platform": None,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    },
    # Firefox 133 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
        "Accept-Language": "bg,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-CH-UA": None,
        "Sec-CH-UA-Mobile": None,
        "Sec-CH-UA-Platform": None,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    },
    # Chrome 130 on Windows 11 (slightly older version for variety)
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-CH-UA": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    },
]


def get_random_profile() -> dict[str, str]:
    """
    Get a random browser profile with realistic headers.

    Returns a copy of the profile with None values removed (e.g., Firefox
    profiles don't include Sec-CH-UA headers).
    """
    profile = random.choice(BROWSER_PROFILES)
    # Remove None values (e.g., Firefox doesn't have Sec-CH-UA headers)
    return {k: v for k, v in profile.items() if v is not None}


def get_profile_by_browser(browser: str) -> dict[str, str]:
    """
    Get a random profile for a specific browser.

    Args:
        browser: One of "chrome", "firefox", "edge"

    Returns:
        A browser profile dict with headers

    Raises:
        ValueError: If browser is not recognized
    """
    browser = browser.lower()
    browser_filters = {
        "chrome": lambda p: "Chrome" in p["User-Agent"] and "Edg" not in p["User-Agent"],
        "firefox": lambda p: "Firefox" in p["User-Agent"],
        "edge": lambda p: "Edg" in p["User-Agent"],
    }

    if browser not in browser_filters:
        raise ValueError(f"Unknown browser: {browser}. Use 'chrome', 'firefox', or 'edge'")

    matching = [p for p in BROWSER_PROFILES if browser_filters[browser](p)]
    profile = random.choice(matching)
    return {k: v for k, v in profile.items() if v is not None}
