# Bulgarian Real Estate Scraper

Scrapes property listings from Bulgarian real estate websites and saves results to CSV.

## Supported Sites

| Site | Type | URL |
|------|------|-----|
| imot.bg | HTML | https://www.imot.bg |
| imoti.net | HTML | https://www.imoti.net |
| homes.bg | JSON API | https://www.homes.bg |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run all scrapers:
```bash
python main.py
```

Run a specific scraper:
```bash
python main.py --scraper_name ImotBg
python main.py --scraper_name ImotiNet
python main.py --scraper_name HomesBg
```

Scrape a specific URL directly (prints to console):
```bash
python main.py --scraper_name ImotBg --url "https://www.imot.bg/obiavi/prodazhbi/grad-sofiya/..."
python main.py --scraper_name HomesBg --url "https://www.homes.bg/api/offers?..."
python main.py --scraper_name ImotiNet --url "https://www.imoti.net/bg/obiavi/r/prodava/sofia/?page=12&sid=gFM8jD"
```

Save results to file when using --url:
```bash
python main.py --scraper_name ImotBg --url "https://www.imot.bg/..." --save
```

Example output:
```
Found 25 listings:

  price currency    city neighborhood property_type                                        details_url
 150000      EUR   София     Лозенец     двустаен  https://www.imot.bg/pcgi/imot.cgi?act=5&adession=...
 180000      EUR   София      Изгрев    тристаен  https://www.imot.bg/pcgi/imot.cgi?act=5&adession=...
```

Custom output folder:
```bash
python main.py --scraper_name ImotBg --result_folder output
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
    "ImotiNet": {
        "urls": [
            {"url": "https://www.imoti.net/bg/obiavi/...", "name": "Search 1"}
        ]
    },
    "HomesBg": {
        "neighborhoods": [
            {"id": 487, "name": "Lozenets"}
        ],
        "include_land": true
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
- `results/raw/{site}/` - Raw scraped data
- `results/processed/{site}/` - Transformed data with normalized fields

## Architecture

```
src/
├── core/
│   ├── parser.py      # BaseParser ABC, Field dataclass
│   ├── scraper.py     # GenericScraper
│   ├── transforms.py  # Transform functions
│   └── models.py      # ListingData Pydantic model
├── sites/
│   ├── imotbg.py      # imot.bg parser
│   ├── imotinet.py    # imoti.net parser
│   └── homesbg.py     # homes.bg parser
└── infrastructure/
    └── clients/
        ├── http_client.py
        └── email_client.py
```

### Adding a New Site

1. Create `src/sites/newsite.py`:

```python
from src.core.parser import BaseParser, Field, SiteConfig
from src.core.transforms import parse_price, extract_currency

class NewSiteParser(BaseParser):
    config = SiteConfig(
        name="newsite",
        base_url="https://newsite.bg",
        encoding="utf-8",
        source_type="html",  # or "json"
        rate_limit_seconds=1.0,
    )

    class Fields:
        price = Field("price_text", parse_price)
        currency = Field("price_text", extract_currency)
        # ... more fields

    @staticmethod
    def build_urls(config: dict) -> list[str]:
        return [item["url"] for item in config.get("urls", [])]

    def extract_listings(self, soup):
        for item in soup.select(".listing"):
            yield {
                "price_text": self.get_text(".price", item),
                # ... more fields
            }

    def get_next_page_url(self, soup, current_url, page_number):
        # Return next page URL or None
        pass
```

2. Register in `src/sites/__init__.py`:

```python
from src.sites.newsite import NewSiteParser

SITE_PARSERS = {
    # ...
    "NewSite": NewSiteParser,
}
```

3. Add URLs to `url_configs.json`

## Testing

```bash
pytest
pytest --cov=src --cov-report=term-missing
```

## GitHub Actions

The scraper runs automatically twice daily (6:00 and 18:00 UTC) via GitHub Actions.

- Sites run in parallel
- URLs within each site run sequentially (rate limiting)
- Results committed in a single commit after all scrapers finish

## License

MIT
