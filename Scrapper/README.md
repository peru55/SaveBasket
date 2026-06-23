# Ethical Scrapper for SaveBasket

Scrapes product data from Kenyan supermarket storefronts:

- **Naivas** (`naivas.online`) — Bagisto/Livewire storefront
- **Quickmart** (`quickmart.co.ke`) — Growcer storefront (requires delivery location)
- **Carrefour** (`carrefour.ke`) — Spartacus/Hybris OCC API + HTML fallback

## Setup

```bash
cd Scrapper
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Usage

```bash
python run_scraper.py "https://www.naivas.online/brookside-fresh-milk-1l"
python run_scraper.py "https://www.quickmart.co.ke/brookside-uht-fino-carton-500ml-36"
python run_scraper.py "https://www.carrefour.ke/mafken/en/uht-milk-full-fat/brookside-uht-whole-milk-tca-200ml/p/43282"
```

Expected output:

```text
Parsed result: {'name': 'Brookside Fresh Milk 1L', 'title': 'Brookside Fresh Milk 1L', 'price': 135.0, 'currency': 'KES', 'image_url': '...', 'category': '...', 'availability': 'in_stock', 'source': 'Naivas', 'normalized_name': 'brookside fresh milk 1l'}
```

## Architecture

- `scraper.py` owns HTTP behavior: robots.txt checks, cache, retries, logging, rate limiting, URL normalization, and final product validation.
- `naivas.py`, `quickmart.py`, and `carrefour.py` only parse supermarket-specific HTML/API shapes.
- `product.py` defines the stable output contract and shared normalization helpers.
- `SITE_PARSERS` in `scraper.py` is the supermarket registry. Add Chandarana or CleanShelf by creating a parser module and registering `("domain", "Source name", parse_func)`.

All parser outputs are validated into:

```python
{
    "name": str | None,
    "title": str | None,  # backward-compatible alias
    "price": float | None,
    "currency": "KES",
    "image_url": str | None,
    "category": str | None,
    "availability": "in_stock" | "out_of_stock" | "unknown",
    "source": str,
    "normalized_name": str | None,
}
```

## Product matching strategy

Use `normalized_name` as a first-pass blocking key, then improve matching with:

- brand extraction from a curated brand dictionary
- package size parsing (`500ml`, `1 l`, `2kg`, `10 pieces`) into normalized units
- token similarity after removing supermarket-only marketing words
- optional barcode/SKU matching when a legal data feed provides it

The production match key should combine brand, normalized product name, package size, and unit count. Price should not be used for identity because it changes frequently.

## Carrefour alternatives

If Carrefour blocks scraping with robots.txt, CDN, or anti-bot controls, do not bypass access restrictions in production. Prefer:

- an official partner/API agreement or approved product feed
- affiliate/catalog exports if available
- manual upload of Carrefour price lists from authorized files
- user-submitted receipts or basket screenshots with consent
- a scheduled browser workflow only when it respects Carrefour terms and robots policy

## Notes

- **Naivas**: Product pages use slug URLs without `.html`. An age-gate overlay may hide content on `.html` links; the scraper normalizes URLs automatically and can fall back to on-site search.
- **Quickmart**: The Growcer storefront requires a delivery location before product/search pages work. The scraper sets a default Nairobi location automatically on first Quickmart request.
- **Carrefour**: Uses compliant HTML/API parsing when available. Some networks receive bot-blocked empty responses; treat repeated blocks as a data-access issue rather than an engineering failure.

## Tests

```bash
python -m unittest test_scraper.py
```

Only run this against sites you have permission to access. Respect each site's terms of service and rate limits.
