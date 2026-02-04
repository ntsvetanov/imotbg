# Bulgarian Real Estate Scraper

Scrapes property listings from Bulgarian real estate websites and saves results to CSV.

## Supported Sites

| Site | Type | URL |
|------|------|-----|
| AloBg | HTML | https://www.alo.bg |
| BazarBg | HTML | https://bazar.bg |
| BulgarianProperties | HTML | https://www.bulgarianproperties.com |
| HomesBg | JSON API | https://www.homes.bg |
| ImotBg | HTML | https://www.imot.bg |
| ImotiCom | HTML | https://imoti.com |
| ImotiNet | HTML | https://www.imoti.net |
| Luximmo | HTML | https://www.luximmo.bg |
| Suprimmo | HTML | https://suprimmo.bg |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Scrape (Download + Process)

Run all scrapers:
```bash
python main.py scrape
```

Run a specific site:
```bash
python main.py scrape --site ImotBg
python main.py scrape --site HomesBg
python main.py scrape --site Suprimmo
```

### Download Only (Raw Data)

```bash
python main.py download --site ImotBg
```

### Process Only (Transform Raw Data)

```bash
python main.py process --site ImotBg
```

### Reprocess Historical Data

Reprocess with updated transformer logic:
```bash
# Reprocess a specific folder
python main.py reprocess --site ImotBg --folder sofia

# Reprocess a specific file
python main.py reprocess --site ImotBg --file results/raw/ImotBg/sofia/2024-01-15.csv

# Reprocess all historical data
python main.py reprocess --site ImotBg --all

# Output to new files instead of overwriting
python main.py reprocess --site ImotBg --folder sofia --output new
```

### Custom Output Folder

```bash
python main.py scrape --site ImotBg --result_folder output
```

### Fetch Single URL (Quick Test)

Fetch a URL and output results to console:
```bash
# Basic fetch (outputs table to console)
python main.py fetch --site Suprimmo --url "https://www.suprimmo.bg/prodajba/..."

# Limit pages for faster results
python main.py fetch --site Suprimmo --url "https://www.suprimmo.bg/prodajba/..." --pages 1

# Also save to CSV file
python main.py fetch --site ImotBg --url "https://www.imot.bg/obiavi/..." --save

# Save to specific file
python main.py fetch --site HomesBg --url "https://www.homes.bg/api/..." --save --output results.csv
```

Example output:
```
Fetched 24 listings from Suprimmo:

    price original_currency   city   neighborhood property_type   area floor  details_url
 185000.0               EUR  София  Сухата река      двустаен   74.0       https://...
 480000.0               EUR  София      Лозенец      тристаен  110.9       https://...
```

## Configuration

### Search URLs

Edit `url_configs.json` to configure search URLs for each site:

```json
{
    "ImotBg": {
        "urls": [
            {"url": "https://www.imot.bg/obiavi/prodazhbi/...", "name": "Sofia Apartments"}
        ]
    },
    "HomesBg": {
        "neighborhoods": [
            {"id": 487, "name": "Lozenets"}
        ],
        "include_land": true
    },
    "Suprimmo": {
        "urls": [
            {"url": "https://suprimmo.bg/...", "name": "Sofia Sales"}
        ]
    }
}
```

### Email Notifications (Optional)

Set environment variables for Mailtrap email notifications on failures:

```bash
export MAILTRAP_HOST=smtp.mailtrap.io
export MAILTRAP_SENDER_EMAIL=sender@example.com
export MAILTRAP_SEND_TO_EMAIL=recipient@example.com
export MAILTRAP_TOKEN=your_token
```

## Output

Results are saved to:
- `results/raw/{site}/` - Raw extracted data (before transformation)
- `results/processed/{site}/` - Transformed data with normalized fields

### Output Fields

All prices are converted to EUR. The output includes:

| Field | Description |
|-------|-------------|
| `site` | Source website |
| `price` | Price in EUR |
| `original_currency` | Original currency (EUR/BGN) |
| `price_per_m2` | Price per square meter |
| `city` | Normalized city name |
| `neighborhood` | Normalized neighborhood |
| `property_type` | Type (едностаен, двустаен, etc.) |
| `offer_type` | Sale or rent |
| `area` | Area in m² |
| `floor` | Floor number |
| `details_url` | Link to listing |
| `fingerprint_hash` | Duplicate detection hash |

## Architecture

The scraper uses a two-stage pipeline: **Extractor** (site-specific) → **Transformer** (site-agnostic).

```
src/
├── core/
│   ├── extractor.py    # BaseExtractor ABC, SiteConfig
│   ├── transformer.py  # Site-agnostic normalization
│   ├── models.py       # RawListing, ListingData models
│   ├── downloader.py   # Download orchestration
│   ├── processor.py    # Processing orchestration
│   └── enums.py        # City, Neighborhood, PropertyType enums
├── sites/
│   ├── imotbg.py       # ImotBgExtractor
│   ├── imotinet.py     # ImotiNetExtractor
│   ├── homesbg.py      # HomesBgExtractor
│   ├── suprimmo.py     # SuprimmoExtractor
│   ├── luximmo.py      # LuximmoExtractor
│   ├── alobg.py        # AloBgExtractor
│   ├── bazarbg.py      # BazarBgExtractor
│   ├── bulgarianproperties.py  # BulgarianPropertiesExtractor
│   └── imoticom.py     # ImotiComExtractor
└── infrastructure/
    └── clients/
        ├── http_client.py
        └── email_client.py
```

### Data Flow

```
HTML/JSON → Extractor.extract_listings() → RawListing → Transformer.transform() → ListingData → CSV
```

1. **Extractor**: Parses site-specific HTML/JSON into `RawListing` (raw text fields)
2. **Transformer**: Normalizes `RawListing` into `ListingData` (parsed, validated, EUR prices)

### Adding a New Site

1. Create `src/sites/newsite.py`:

```python
from src.core.extractor import BaseExtractor, SiteConfig
from src.core.models import RawListing

class NewSiteExtractor(BaseExtractor):
    config = SiteConfig(
        name="newsite",
        base_url="https://newsite.bg",
        encoding="utf-8",
        source_type="html",  # or "json"
        rate_limit_seconds=1.0,
    )

    @staticmethod
    def build_urls(config: dict) -> list[str]:
        return [item["url"] for item in config.get("urls", [])]

    def extract_listings(self, soup):
        for item in soup.select(".listing"):
            yield RawListing(
                site=self.config.name,
                price_text=self._get_text(".price", item),
                location_text=self._get_text(".location", item),
                title=self._get_text(".title", item),
                area_text=self._get_text(".area", item),
                floor_text=self._get_text(".floor", item),
                details_url=self._get_attr("a", "href", item),
                # ... more fields
            )

    def get_next_page_url(self, soup, current_url, page_number):
        # Return next page URL or None to stop pagination
        next_link = soup.select_one("a.next")
        return next_link["href"] if next_link else None
```

2. Register in `src/sites/__init__.py`:

```python
from src.sites.newsite import NewSiteExtractor

SITE_EXTRACTORS = {
    # ...
    "NewSite": NewSiteExtractor,
}
```

3. Add URLs to `url_configs.json`

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_imotbg.py -v
```

## GitHub Actions

The scraper runs automatically twice daily (6:00 and 18:00 UTC) via GitHub Actions.

- Sites run in parallel
- URLs within each site run sequentially (rate limiting)
- Results committed in a single commit after all scrapers finish

## License

MIT
