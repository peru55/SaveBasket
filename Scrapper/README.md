# SaveBasket Scrapper

The `Scrapper/` folder contains the price collection pipeline for SaveBasket. It can scrape individual product pages, persist local JSON snapshots, run a batch of saved product URLs, and push scraped products to the Django backend ingestion endpoint.

The scraper is intentionally conservative: it respects robots rules where available, rate-limits requests, uses short-lived caching, and keeps product identity separate from price.

---

## Supported Stores

| Store | Domain | Notes |
| --- | --- | --- |
| Naivas | `naivas.online` | Product pages and search fallback |
| Quickmart | `quickmart.co.ke` | Growcer storefront; scraper sets a default Nairobi delivery location |
| CleanShelf | `cleanshelf.online` | API/category helpers and product parser |
| Carrefour | `carrefour.ke` | HTML/JSON-LD/OCC parsing where access is allowed; may be blocked by CDN/network rules |

---

## Setup

```powershell
cd "C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\Scrapper"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

For commands below, keep the scraper virtual environment active unless you call `venv\Scripts\python.exe` explicitly.

---

## Scrape One Product

```powershell
python run_scraper.py "https://www.naivas.online/brookside-fresh-milk-1l"
```

Useful options:

```powershell
python run_scraper.py "PRODUCT_URL" --backend http://127.0.0.1:8000
python run_scraper.py "PRODUCT_URL" --backend http://127.0.0.1:8000 --key YOUR_SCRAPER_API_KEY
python run_scraper.py "PRODUCT_URL" --backend http://127.0.0.1:8000 --push-unchanged
python run_scraper.py "PRODUCT_URL" --no-json
```

What happens on a successful scrape:

1. The product page is fetched and parsed.
2. The result is normalized into the shared product contract.
3. A JSON snapshot is created or updated under `Scrapper/data/`.
4. If `--backend` is provided, changed products are pushed to `/api/scraper/ingest/`.
5. If `--push-unchanged` is also provided, unchanged products are pushed too.

Example output:

```text
Parsed result: {
  'name': 'Brookside Fresh Milk 1L',
  'title': 'Brookside Fresh Milk 1L',
  'price': 135.0,
  'currency': 'KES',
  'image_url': '...',
  'category': '...',
  'availability': 'in_stock',
  'source': 'Naivas',
  'normalized_name': 'brookside fresh milk 1l'
}
```

---

## Scrape Multiple Products

Put product URLs in `ci_jobs.txt`, one URL per line. Comments and headings can start with `#`.

```text
### naivas
https://www.naivas.online/brookside-fresh-milk-1l
https://www.naivas.online/elianto-cooking-oil-1ltr

### quickmart
https://www.quickmart.co.ke/elianto-corn-oil-1l-55
https://www.quickmart.co.ke/elianto-corn-oil-2lt-10

### cleanshelf
https://cleanshelf.online/product/elianto-1ltr
```

Check that jobs are being loaded:

```powershell
python ci_runner.py --list-jobs
```

Run the batch and push to the backend:

```powershell
python ci_runner.py --backend http://127.0.0.1:8000
```

With an API key:

```powershell
python ci_runner.py --backend http://127.0.0.1:8000 --key YOUR_SCRAPER_API_KEY
```

Dry-run without pushing:

```powershell
python ci_runner.py --dry-run
```

Use a different jobs file:

```powershell
python ci_runner.py --jobs-file path\to\my_jobs.txt --backend http://127.0.0.1:8000
```

`ci_runner.py` resolves the default `ci_jobs.txt` relative to itself, so it works whether you run it from the project root or from inside `Scrapper/`.

---

## Daily Automation On Windows

Use Windows Task Scheduler once the backend is running locally or hosted.

Create a task with:

Program/script:

```text
C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\Scrapper\venv\Scripts\python.exe
```

Arguments:

```text
ci_runner.py --backend http://127.0.0.1:8000
```

Start in:

```text
C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\Scrapper
```

If the backend has `SCRAPER_API_KEY` set, add:

```text
--key YOUR_SCRAPER_API_KEY
```

When the backend is deployed, replace `http://127.0.0.1:8000` with the hosted backend URL.

---

## Push Existing JSON Snapshots

If products already exist under `Scrapper/data/`, push their current snapshots to the backend with:

```powershell
python sync_json_to_backend.py --backend http://127.0.0.1:8000
```

With an API key:

```powershell
python sync_json_to_backend.py --backend http://127.0.0.1:8000 --key YOUR_SCRAPER_API_KEY
```

This is useful after changing backend matching logic or when you want ingestion-history rows for already-scraped products.

---

## Backend Payload

The backend expects:

```json
{
  "source": "Naivas",
  "branch": {
    "name": "Website",
    "city": "Nairobi"
  },
  "products": [
    {
      "name": "Elianto Corn Oil 1L",
      "title": "Elianto Corn Oil 1L",
      "price": 599.0,
      "currency": "KES",
      "url": "https://www.quickmart.co.ke/elianto-corn-oil-1l-55",
      "image_url": "https://example.com/image.jpg",
      "category": "Cooking Oil",
      "availability": "in_stock",
      "source": "Quickmart",
      "normalized_name": "elianto corn oil 1l"
    }
  ]
}
```

`push_to_backend.py`, `run_scraper.py`, and `ci_runner.py` build this shape for you.

---

## Product Contract

Every parser should return a dictionary with this shape:

```python
{
    "name": str | None,
    "title": str | None,
    "price": float | None,
    "currency": "KES",
    "image_url": str | None,
    "category": str | None,
    "availability": "in_stock" | "out_of_stock" | "unknown",
    "source": str,
    "normalized_name": str | None,
    "url": str | None,
}
```

`title` remains for backwards compatibility. Prefer filling both `name` and `title` when adding new parsers.

---

## Local JSON Snapshots

Successful scrapes are persisted under:

```text
Scrapper/data/<source>/...
```

Each snapshot tracks:

- current product data
- source URL
- stable product key
- created/updated timestamps
- price history events

Update strategy:

- New product: create a JSON file.
- Same product, same price: skip writing.
- Same product, changed price: update the file and append a history event.
- Identity priority: URL path, SKU, barcode, normalized name, then hash fallback.

---

## Product Identity Notes

The backend owns final product matching. The scraper should still send the cleanest possible product name, URL, source, image, and price.

Important rules:

- Price must never be used as product identity.
- Keep package sizes in names when available: `1L`, `2Lt`, `500ml`, `2kg`.
- Unit variants matter and are normalized in the backend: `ltr`, `lt`, `litre`, and `l` all become `l`.
- Store-specific names can differ. The backend uses aliases, canonical category/type, brand, size, and unit to match products.
- If a store returns a 2L product while the URL says 1L, the scraper or job URL is wrong and should be reviewed.

Recent example:

```text
Elianto Corn Oil 1L   -> Quickmart 599
Elianto Corn Oil 2Lt  -> Quickmart 1197
```

These must stay separate because their sizes differ.

---

## Architecture

| File | Purpose |
| --- | --- |
| `scraper.py` | HTTP behavior, robots checks, caching, retries, rate limiting, parser dispatch |
| `product.py` | Product validation and shared normalization helpers |
| `naivas.py` | Naivas parser |
| `quickmart.py` | Quickmart parser and search fallback |
| `cleanshelf.py` | CleanShelf parser and API helpers |
| `carrefour.py` | Carrefour parser, JSON-LD, and OCC fallback |
| `json_store.py` | Local JSON snapshots and price history |
| `run_scraper.py` | One-product scrape command |
| `ci_runner.py` | Batch job runner using `ci_jobs.txt` |
| `push_to_backend.py` | Push a payload/file/URL to backend ingestion |
| `sync_json_to_backend.py` | Push existing JSON snapshots to backend |

---

## Tests

Run scraper tests:

```powershell
python -m unittest discover -s . -p "test_*.py"
```

Run a focused test file:

```powershell
python -m unittest test_scraper.py
python -m unittest test_json_store.py
```

---

## Troubleshooting

### `No URLs to process`

Check what the runner sees:

```powershell
python ci_runner.py --list-jobs
```

If you use a custom file, pass it explicitly:

```powershell
python ci_runner.py --jobs-file path\to\jobs.txt --list-jobs
```

### Product appears with the wrong price

Check:

1. Is the URL in `ci_jobs.txt` for the correct size?
2. Did the parser return the correct title and price?
3. Did the backend match the product to the correct size/unit?
4. Did `ProductPrice` get updated, not only `StoreProduct`?

For known size-sensitive products, include both URLs separately:

```text
https://www.quickmart.co.ke/elianto-corn-oil-1l-55
https://www.quickmart.co.ke/elianto-corn-oil-2lt-10
```

### Backend receives nothing

Confirm the backend is running:

```powershell
curl http://127.0.0.1:8000/api/products/
```

Then test one product:

```powershell
python run_scraper.py "PRODUCT_URL" --backend http://127.0.0.1:8000 --push-unchanged
```

### Carrefour fails repeatedly

Carrefour may return empty or blocked responses depending on network/CDN rules. Treat repeated blocks as a data-access limitation. Prefer approved feeds, manual imports, or an official partner/API arrangement.

---

## Responsible Scraping

- Respect each site's terms of service.
- Keep request volume low.
- Do not bypass access controls.
- Prefer official feeds or partnerships for production use.
- Use cached JSON snapshots to avoid unnecessary repeat requests.
