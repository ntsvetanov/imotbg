#!/usr/bin/env python3
"""
One-time script to capture HTML/JSON fixtures from live sites.

Usage:
    python scripts/capture_fixtures.py [site_name]

    # Capture all sites:
    python scripts/capture_fixtures.py

    # Capture specific site:
    python scripts/capture_fixtures.py alobg

Note: Some sites (imotbg, bazarbg, imoticom, suprimmo, luximmo, bulgarianproperties)
use Cloudflare protection and require cloudscraper.
"""

import json
import sys
import time
from pathlib import Path

import cloudscraper
import httpx

# Sample URLs for each site (one representative URL per site)
SITE_URLS = {
    "alobg": {
        "url": "https://www.alo.bg/obiavi/imoti-prodajbi/apartamenti-stai/?region_id=22&location_ids=4342",
        "use_cloudscraper": False,
        "is_json": False,
    },
    "bazarbg": {
        "url": "https://bazar.bg/obiavi/prodazhba-apartamenti/sofia?asize[]=2&asize[]=3&currency=2",
        "use_cloudscraper": True,
        "is_json": False,
    },
    "bulgarianproperties": {
        # Main listing page - returns server-rendered HTML with listings
        "url": "https://www.bulgarianproperties.bg/prodazhba-imot/index.html",
        "use_cloudscraper": True,
        "is_json": False,
    },
    "homesbg": {
        "url": "https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0&locationId=1&typeId=ApartmentSell&neighbourhoods%5B%5D=487",
        "use_cloudscraper": False,
        "is_json": True,
    },
    "imotbg": {
        "url": "https://www.imot.bg/obiavi/prodazhbi/grad-sofiya/dianabad/dvustaen",
        "use_cloudscraper": True,
        "is_json": False,
    },
    "imoticom": {
        "url": "https://www.imoti.com/prodazhbi/grad-sofiya/dvustaini",
        "use_cloudscraper": True,
        "is_json": False,
    },
    "imotinet": {
        "url": "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=1",
        "use_cloudscraper": False,
        "is_json": False,
    },
    "luximmo": {
        "url": "https://www.luximmo.bg/prodajba/bulgaria/oblast-sofiya/sofiya-luksozni-imoti/po-tip-apartamenti/index.html",
        "use_cloudscraper": True,
        "is_json": False,
    },
    "suprimmo": {
        "url": "https://www.suprimmo.bg/prodajba/bulgaria/oblast-sofiya/sofiya-imoti/po-tip-apartamenti/",
        "use_cloudscraper": True,
        "is_json": False,
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def capture_site(site_name: str, config: dict, output_dir: Path) -> bool:
    """Capture HTML/JSON from a single site."""
    url = config["url"]
    use_cloudscraper = config["use_cloudscraper"]
    is_json = config["is_json"]

    ext = "json" if is_json else "html"
    output_file = output_dir / f"{site_name}.{ext}"

    print(f"Capturing {site_name}...")
    print(f"  URL: {url[:80]}{'...' if len(url) > 80 else ''}")

    try:
        if use_cloudscraper:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, headers=HEADERS, timeout=30)
        else:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=HEADERS)

        response.raise_for_status()

        if is_json:
            # Validate JSON and pretty-print
            data = response.json()
            output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            output_file.write_text(response.text, encoding="utf-8")

        size_kb = len(response.text) / 1024
        print(f"  Saved to {output_file.name} ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def main():
    # Determine output directory (relative to script location)
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "tests" / "fixtures" / "html"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which sites to capture
    if len(sys.argv) > 1:
        sites_to_capture = sys.argv[1:]
        invalid = set(sites_to_capture) - set(SITE_URLS.keys())
        if invalid:
            print(f"Unknown sites: {invalid}")
            print(f"Available: {list(SITE_URLS.keys())}")
            sys.exit(1)
    else:
        sites_to_capture = list(SITE_URLS.keys())

    print(f"Capturing {len(sites_to_capture)} site(s) to {output_dir}\n")
    print("=" * 50)

    results = {}
    for i, site_name in enumerate(sites_to_capture):
        if i > 0:
            # Rate limit between requests
            time.sleep(2)

        config = SITE_URLS[site_name]
        results[site_name] = capture_site(site_name, config, output_dir)
        print()

    # Summary
    print("=" * 50)
    succeeded = sum(results.values())
    failed = len(results) - succeeded
    print(f"Done: {succeeded} succeeded, {failed} failed")

    if failed:
        print("Failed sites:", [s for s, ok in results.items() if not ok])
        sys.exit(1)


if __name__ == "__main__":
    main()
