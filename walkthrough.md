# SaveBasket Walkthrough

SaveBasket is a grocery savings platform for comparing basket prices across Kenyan supermarkets. The project currently has three working parts:

- `backend/`: Django REST API, product matching, basket comparison, ingestion history, and admin review queue.
- `frontend/`: Flutter app for web, mobile, and desktop.
- `Scrapper/`: Python scraper and JSON persistence pipeline that can push products into the backend.

---

## Current Project Structure

```text
SaveBasket/
├── backend/          Django REST API
├── frontend/         Flutter client
├── Scrapper/         Supermarket scraper and ingestion helpers
├── ERD.md            Data model notes
└── walkthrough.md    Current project guide
```

---

## Backend

The backend is a Django 5 API using Django REST Framework, JWT auth, and SQLite for local development. It can switch to PostgreSQL through `.env` database settings.

### Apps

| App | Purpose |
| --- | --- |
| `supermarkets` | Supermarket chains and branches |
| `products` | Canonical products, store-specific products, branch prices, raw scraped rows, ingestion history, import review queue |
| `baskets` | User baskets, basket items, and basket comparison |
| `users` | Registration and JWT token endpoints |

### Main Models

| Model | Notes |
| --- | --- |
| `Product` | Canonical product record with normalized name, brand, size, unit, and optional image |
| `StoreProduct` | Store-specific product row linked to one canonical `Product`; unique by `(product, store_name)` |
| `ProductPrice` | Branch-level price linked to `Product` and `Branch` |
| `RawScrapedProduct` | Raw scraper item saved before matching |
| `IngestionHistory` | Audit record for each scraper ingestion run |
| `ProductImportReview` | Admin queue for possible duplicate products and low-confidence matches |
| `Basket` / `BasketItem` | User basket and selected products |

### API Routes

Base URL: `http://127.0.0.1:8000/api/`

| Route | Purpose |
| --- | --- |
| `/supermarkets/` | List and manage supermarkets |
| `/branches/` | List and manage branches; supports `?supermarket_id=` |
| `/products/` | Product search; supports `?search=` and `?category=` |
| `/prices/` | Branch-level prices; supports `?product_id=` and `?branch_id=` |
| `/baskets/` | Authenticated basket CRUD |
| `/baskets/{id}/add_item/` | Add product to basket |
| `/baskets/{id}/remove_item/` | Remove product from basket |
| `/baskets/{id}/update_item_quantity/` | Update quantity |
| `/baskets/{id}/compare/` | Compare basket totals across stores |
| `/products/image-proxy/?url=...` | Proxy external product images for frontend display |
| `/scraper/ingest/` | Accept scraper payloads |
| `/auth/register/` | Register user |
| `/auth/token/` | Obtain JWT access and refresh token |
| `/auth/token/refresh/` | Refresh access token |

### Product Matching And Import Review

Scraper ingestion flows through `ProductMatchService`:

1. Save the incoming row as `RawScrapedProduct`.
2. Normalize the product name and extract brand, size, and unit.
3. Match against existing canonical `Product` records.
4. Create or update the correct `StoreProduct` using `(product, store_name)`.
5. Create or update branch-level `ProductPrice` when a branch is provided.
6. Mark the raw row as processed.

The matcher protects against split products such as `Pembe Flour` or `Brookside 500ml` by using normalized names, brand compatibility, size compatibility, token identity scoring, and a broad fallback for older products with missing size/unit data.

The admin review queue catches cases that should not be silently trusted:

- `possible_duplicate`: a new canonical product was created, but an existing product looked similar.
- `low_confidence_match`: an automatic match was accepted, but the score is below the high-confidence threshold.

Relevant settings:

```python
PRODUCT_SIMILARITY_THRESHOLD = 0.8
PRODUCT_LOW_CONFIDENCE_MATCH_THRESHOLD = 0.92
PRODUCT_REVIEW_MIN_SIMILARITY = 0.55
SCRAPER_API_KEY = optional
```

Open Django admin and use **Product import reviews** to mark items as reviewed, ignored, or open.

### Basket Comparison

Basket comparison groups prices by supermarket and picks the cheapest available branch/channel price for each product. This avoids showing the same supermarket multiple times because of branch-level records.

Results include:

- total basket price
- number of available products
- missing products
- completeness flag
- per-product price breakdown

Complete baskets are ranked ahead of incomplete baskets, then sorted by total cost.

### Product Images

Product serializers return proxied image URLs. If `Product.image_url` is missing, the API falls back to the first linked `StoreProduct.scraped_image_url`. The frontend then loads images through:

```text
/api/products/image-proxy/?url=<encoded remote image URL>
```

This helps avoid supermarket CDN/hotlink failures in the Flutter app.

---

## Frontend

The frontend is a Flutter Material 3 app using Provider state management.

### Main Features

- Login and registration with JWT.
- Responsive layout for mobile, tablets, laptops, and desktop.
- Web/tablet/laptop auth screens use `assets/app_images/splash_screen_background.png`.
- Product search with product images.
- Basket management with quantity controls.
- Ranked store comparison cards.
- Comparison detail screen with missing items and price breakdown.
- Static supermarket logos from `assets/logos/`, including CleanShelf.

### Key Files

| File | Purpose |
| --- | --- |
| `lib/services/api_service.dart` | Backend API client and token retry |
| `lib/services/auth_service.dart` | Auth requests and secure token storage |
| `lib/providers/auth_provider.dart` | Login/register/session state |
| `lib/providers/basket_provider.dart` | Basket, search, and comparison state |
| `lib/screens/home_screen.dart` | Main responsive app shell/dashboard |
| `lib/screens/search_screen.dart` | Product search UI |
| `lib/screens/basket_screen.dart` | Basket and ranked store results |
| `lib/screens/comparison_detail_screen.dart` | Detailed store comparison |
| `lib/screens/login_screen.dart` | Login UI |
| `lib/screens/register_screen.dart` | Registration UI |
| `lib/screens/auth_web_shell.dart` | Large-screen auth background shell |

### Assets

```yaml
assets:
  - assets/logos/
  - assets/app_images/
```

Store logos are local Flutter assets. Product images come from the backend serializer, usually through the image proxy.

---

## Scrapper

The scraper is a standalone Python package for collecting product data from supermarket storefronts.

### Supported Sources

| Source | Status |
| --- | --- |
| Naivas | Product page parser and search fallback |
| Quickmart | Growcer parser with default delivery location setup |
| Carrefour | HTML/JSON-LD/OCC parsing where the site allows access |
| CleanShelf | API/category helpers and parser support |

### Core Files

| File | Purpose |
| --- | --- |
| `scraper.py` | HTTP behavior, caching, retries, robots handling, parser dispatch |
| `product.py` | Stable product contract and normalization |
| `naivas.py` | Naivas parser |
| `quickmart.py` | Quickmart parser/search |
| `carrefour.py` | Carrefour parser/OCC fallback |
| `cleanshelf.py` | CleanShelf parser/API helpers |
| `json_store.py` | Local JSON snapshot persistence and price history |
| `run_scraper.py` | One-product scrape command; can persist and push to backend |
| `push_to_backend.py` | Push one payload/file/url to `/api/scraper/ingest/` |
| `sync_json_to_backend.py` | Backfill existing JSON snapshots into the backend |

### Product Contract

Parsers normalize outputs into this shape:

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
}
```

### Scrape And Push

```bash
cd Scrapper
venv\Scripts\activate
python run_scraper.py "https://www.naivas.online/brookside-fresh-milk-1l" --backend http://127.0.0.1:8000
```

If `SCRAPER_API_KEY` is set in `backend/.env`, pass:

```bash
--key YOUR_KEY
```

By default, unchanged local JSON snapshots are not pushed. Add `--push-unchanged` when you want an ingestion-history row even if the product did not change.

---

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional development seed:

```bash
python manage.py seed_data --dev
```

The seeder is guarded by `--dev` and `DEBUG=True`.

### Frontend

```bash
cd frontend
flutter pub get
flutter run
```

For web during development:

```bash
flutter run -d chrome
```

### Scrapper

```bash
cd Scrapper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_scraper.py "https://www.naivas.online/brookside-fresh-milk-1l"
```

---

## Verification

### Backend

```bash
cd backend
.venv\Scripts\python.exe manage.py test products baskets
```

Latest verified result:

```text
26 tests passed
```

### Scrapper

```bash
cd Scrapper
venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
```

Latest verified result:

```text
29 tests passed
```

### Frontend

```bash
cd frontend
flutter analyze
```

Latest verified result:

```text
No issues found
```

---

## Current Integration State

```text
Scrapper ──POST /api/scraper/ingest/──▶ Backend ──REST API──▶ Frontend
   │                                      │
   └── JSON snapshots + price history     └── SQLite locally / PostgreSQL-ready
```

Current status:

- Frontend and backend are connected.
- Scraper can persist JSON snapshots and push changed products to the backend.
- Backend stores ingestion history and raw scraped rows.
- Product matching prevents many duplicate canonical products.
- Admin review queue surfaces possible duplicates and low-confidence matches.
- Product images are proxied through the backend for frontend reliability.

---

## Near-Term Improvements

1. Add admin actions or a management command to merge products directly from `ProductImportReview`.
2. Add a small dashboard for scraper health: last ingestion, failed images, duplicate-review count, and unmatched products.
3. Cache proxied product images locally instead of fetching remote supermarket images every time.
4. Persist the active basket ID on the frontend so returning users resume the same basket.
5. Add store-level explanations for missing products in comparison results.
6. Expand scraper coverage and keep supermarket parsers behind tests before using them for bulk imports.

---

## Issue Log: Blueband 500g Naivas Price

Date checked: 2026-06-29

### Symptom

Blueband Margarine 500g from Naivas was showing as KES 1,199 instead of the expected KES 275.

### Root Cause

The bad value came from the Naivas scraper before import. The importer preserved the scraped value correctly, but the scraper was reading an unrelated DOM price from the page. The Naivas product page included the correct product price in JSON-LD structured data, but that JSON-LD was HTML-escaped, so the parser skipped it and later saw another product/promo price.

### Fix

- Updated the Naivas parser to prefer product JSON-LD offer prices before broad DOM price scanning.
- Added support for HTML-escaped JSON-LD.
- Kept the existing listing-page safeguard that matches product cards by requested URL slug.
- Canonicalized `Blueband` to `blue band` in product matching so variant-aware identity works across store naming differences.
- Ensured Blue Band products without an explicit variant, such as Original, Choco, or Vanilla, do not auto-merge into variant-specific products.

### Local Data Repair

The existing local database already contained the old bad scrape, so these rows were corrected:

- `RawScrapedProduct`: Naivas Blueband Margarine 500g changed to KES 275.
- `StoreProduct`: Naivas Blueband Margarine 500g changed to KES 275.
- `ProductPrice`: Naivas Blueband Margarine 500g changed to KES 275.
- Existing `blueband` product brands were canonicalized to `blue band`.

### Verification

```bash
cd Scrapper
venv\Scripts\python.exe run_scraper.py "https://www.naivas.online/blueband-margarine-500g"
```

Verified parser result:

```text
price: 275.0
```

Relevant tests:

```bash
cd Scrapper
venv\Scripts\python.exe -m unittest test_scraper.py

cd backend
.venv\Scripts\python.exe manage.py test products.tests_services
```

Latest verified result:

```text
Scraper: 31 tests passed
Backend product services: 29 tests passed
```

---

## Admin Workflow: Product Import Reviews

Date added: 2026-06-29

The `ProductImportReview` admin queue is now actionable. It is used to resolve possible duplicate products, low-confidence matches, and missing-variant cases without silently merging products during import.

### Accept Review

Use this when the scraped product is confirmed to be the same real-world product as the candidate product.

Admin action:

```text
Accept: create reviewed alias and merge into candidate
```

This action:

- Creates or updates a `ProductAlias` with `source=reviewed`.
- Links the scraped store-specific name to the selected candidate product.
- Moves the matching `StoreProduct` row to the candidate product.
- Moves matching `ProductPrice` rows when applicable.
- Marks the review as `reviewed`.
- Deletes the duplicate product only when it has no remaining store or price records.

Example:

```text
Naivas Blueband Margarine 500g
CleanShelf Blueband Spread 500Gm
```

can be accepted as aliases for:

```text
Blue Band Original Spread 500G
```

After acceptance, the frontend should show one 500g Blue Band product with multiple supermarket prices instead of separate duplicate cards.

### Reject Review

Use this when the scraped product should remain separate.

Admin action:

```text
Reject: keep products separate
```

This action:

- Marks the review as `ignored`.
- Leaves both products unchanged.
- Does not create aliases.
- Does not move store or price records.

### Manual Status Actions

The older status-only actions still exist:

```text
Mark selected reviews as reviewed
Mark selected reviews as ignored
Reopen selected reviews
```

These only update review status. Use the explicit accept/reject actions when the decision should affect product matching data.

### Verification

```bash
cd backend
.venv\Scripts\python.exe manage.py test products.tests_services
.venv\Scripts\python.exe manage.py test products baskets
```

Latest verified result:

```text
Product service tests: 31 tests passed
Products + baskets tests: 40 tests passed
```


#### Credential safety

Test and production credentials must be created outside the repository and
stored in environment variables or the hosting provider's secret manager.
Never document working usernames, passwords, or secret keys here.
