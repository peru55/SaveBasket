# SaveBasket Implementation Walkthrough

**SaveBasket** is a final-year grocery savings platform for comparing basket prices across Kenyan supermarkets. The project consists of three standalone components: a Django REST backend, a Flutter cross-platform frontend, and a Python web scraper (`Scrapper/`). The scraper is **not yet connected** to the backend; prices currently come from a manual database seeder.

---

## Project Structure

```
SaveBasket/
├── backend/          # Django 5.2 REST API (SQLite locally; PostgreSQL planned)
├── frontend/         # Flutter mobile/web/desktop client
├── Scrapper/         # Ethical price scraper for Naivas, Quickmart, Carrefour
└── walkthrough.md    # This file
```

---

## What Was Built

### 1. Django Backend (`backend/`)

Three domain apps plus authentication:

| App | Purpose |
|-----|---------|
| **`supermarkets`** | `Supermarket` and `Branch` models with latitude, longitude, address, and city fields for spatial mapping |
| **`products`** | `Product` (name, SKU, barcode, category, brand, image) and `ProductPrice` (branch-specific pricing with `source_url` and `updated_at`) |
| **`baskets`** | `Basket` and `BasketItem` models with a `compare_prices()` method that ranks branches by total cost and item completeness |
| **`users`** | JWT registration and token endpoints via `djangorestframework-simplejwt` |

**Database configuration** (`savebasket/settings.py`):
- Uses **SQLite** (`backend/db.sqlite3`) when no `DB_HOST` is set in `.env`
- Switches to **PostgreSQL** when `DB_HOST`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` are provided (planned production setup)

**REST API endpoints** (base: `http://127.0.0.1:8000/api/`):

| Endpoint | Description |
|----------|-------------|
| `/supermarkets/` | List supermarket chains |
| `/branches/` | List branches (filter: `?supermarket_id=`) |
| `/products/` | Search products (`?search=`, `?category=`) |
| `/prices/` | Branch-specific prices (`?product_id=`, `?branch_id=`) |
| `/baskets/` | CRUD for user baskets (requires auth) |
| `/baskets/{id}/add_item/` | Add product to basket |
| `/baskets/{id}/remove_item/` | Remove product from basket |
| `/baskets/{id}/update_item_quantity/` | Update quantity |
| `/baskets/{id}/compare/` | Rank branches by basket total |
| `/auth/register/` | Create account |
| `/auth/token/` | Obtain JWT access + refresh tokens |
| `/auth/token/refresh/` | Refresh access token |

**Basket comparison logic** (`baskets/models.py`):
- Aggregates `ProductPrice` records for all products in a basket
- Computes total cost per branch, tracks missing items, and flags incomplete baskets
- Sorts results: complete baskets first, then by ascending total cost

**Database seeder** — run with:
```bash
python manage.py seed_data
```
Populates Carrefour (Sarit Centre, Junction Mall), Naivas (Westlands, Kilimani), and Quickmart (Lavington) with five staple products (Brookside Milk, Kabras Sugar, Jogoo Maize Meal, Broadways Bread, Fresh Fri Cooking Oil) at varying prices. Some branches intentionally have missing items to test incomplete-basket ranking.

**Dependencies** (`backend/requirements.txt`): Django 5.x, DRF, django-cors-headers, psycopg2-binary, python-dotenv, djangorestframework-simplejwt, requests, beautifulsoup4.

---

### 2. Flutter Frontend (`frontend/`)

A Material 3 client with a forest-green savings theme, responsive layout (mobile bottom nav + desktop side rail), and JWT authentication.

**State management** (Provider):
- `AuthProvider` — login, register, logout, silent token refresh (every 12 minutes), session-expired dialog
- `BasketProvider` — active basket, product search, price comparison results

**Screens**:
- **Login / Register** — JWT auth flow with secure token storage (`flutter_secure_storage`)
- **Dashboard** — savings hero, quick stats, market pulse, fast actions
- **Browse** — product search with add-to-basket controls
- **My Basket** — item list with quantity controls and horizontal comparison cards ("Best Deal", "Incomplete" badges)
- **Comparison Detail** — per-branch breakdown of item availability and totals

**API client** (`lib/services/api_service.dart`):
- Platform-aware base URL: `localhost:8000` (web/desktop), `10.0.2.2:8000` (Android emulator)
- Automatic 401 retry via token refresh

**Dependencies** (`pubspec.yaml`): `http`, `provider`, `flutter_secure_storage`.

---

### 3. Scrapper (`Scrapper/`)

A standalone Python scraper **not yet integrated** with the backend. It is designed to eventually populate `ProductPrice` records with live supermarket data.

**Core class**: `EthicalScraper` (`scraper.py`)

| Feature | Implementation |
|---------|----------------|
| Rate limiting | Per-domain delay (default 1 s) with thread-safe locking |
| robots.txt | Respects disallow rules; allows fetch when robots.txt is missing |
| Caching | `requests-cache` (5-minute TTL) to reduce repeat requests |
| Retries | Exponential backoff via `tenacity` (up to 4 attempts) |
| Timeouts | Naivas: 15 s; Quickmart & Carrefour: 60 s (slow sites) |

**Site-specific parsers**:

| Supermarket | Domain | Parser strategy | Current status |
|-------------|--------|-----------------|----------------|
| **Naivas** | `naivas.online` | Looks for `div.text-xl` title + sibling price; falls back to generic heuristics | **Working** — HTTP fetch succeeds (200); structured parser matches `text-xl` divs and `product-price` correctly |
| **Quickmart** | `quickmart.co.ke` | Growcer storefront: `h1` title + `products-price-new` / `products-price` CSS classes; location cookie set automatically | **Working** — Fetch succeeds after location setup; price extracted from `products-price-new` elements |
| **Carrefour** | `carrefour.ke` | JSON-LD extraction + OCC API fallback; generic HTML heuristics. Uses `cloudscraper` to bypass CDN | **Blocked from non-Kenyan IPs** — Returns empty shell or "Access Denied" via CDN. JSON-LD and OCC API work from Kenyan networks |

**Entry point**:
```bash
cd Scrapper
python run_scraper.py <product_url> [css_selector]
```

**Dependencies** (`Scrapper/requirements.txt`): requests, requests-cache, beautifulsoup4, lxml, tenacity, cloudscraper.

---

## Integration Status

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Scrapper   │ ──X──│   Backend    │◄────│  Frontend   │
│  (standalone)│     │  Django REST │     │   Flutter   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │ SQLite (now) │
                    │ PostgreSQL   │
                    │  (planned)   │
                    └──────────────┘
```

- **Frontend ↔ Backend**: Connected. Flutter calls REST endpoints; basket operations require JWT auth.
- **Scrapper ↔ Backend**: **Not connected.** Prices are seeded manually via `seed_data`. Planned next step: a Django management command or Celery task that runs the scraper and upserts `ProductPrice` records using the `source_url` field.

---

## Validation & Verification

### Backend Unit Tests

```bash
cd backend
python manage.py test
```

**Latest run (June 2026):**
- **10 tests discovered** across `baskets`, `users`, and `users.tests_additional`
- **8 passed**, **1 failed**, **1 error**
- Basket comparison tests (2): **pass** — correctly ranks cheaper stores and prioritizes complete baskets
- Auth token/refresh/protected-endpoint tests: **pass**
- `test_register_creates_user`: **fail** — password `secret123` rejected by Django's password validators (returns 400)
- `test_register` (from `test_register.py`): **error** — this file is a standalone HTTP script, not a unit test; it runs at import time and fails when the server is not running

Core basket logic verified separately:
```bash
python manage.py test baskets
# Result: 2 tests passed
```

### Flutter Static Analysis

```bash
cd frontend
flutter analyze
```

**Latest run:** 6 issues (0 errors, 1 warning, 5 info):
- 5× `use_build_context_synchronously` in `main.dart` and `home_screen.dart`
- 1× unused field `_initialized` in `auth_provider.dart`

The app compiles and runs; these are lint advisories, not blocking errors.

### Scraper Smoke Test

```bash
cd Scrapper
python run_scraper.py https://naivas.online/<product-slug>.html
```

**Naivas**: HTTP 200 fetch confirmed; site-specific parser may fall back to a raw price list if the `text-xl` DOM structure does not match.

**Quickmart / Carrefour**: Fetch or parse failures observed — see Known Issues below.

### Database Seeding

```bash
cd backend
python manage.py seed_data
# Result: Database seeded with 3 supermarkets, 5 branches, 5 products, and branch-specific prices
```

---

## Known Issues & Next Steps

### Scraper (priority)

1. ~~**Quickmart** — Investigate correct product URL patterns; site may return 404 for guessed slugs.~~ **Fixed** — CSS selectors updated to match Growcer's `products-price-new` / `products-price` classes. Search results parser now filters out non-product navigation links. Verified: correctly parses live product pages returning title + price.
2. **Carrefour** — Site uses Next.js with CDN shielding (Akamai/CloudFront). From non-Kenyan IPs, requests return empty shells or "Access Denied" pages. The scraper now has `cloudscraper` fallback and detects blocked pages explicitly. Works from Kenyan networks where JSON-LD and the OCC API (`/occ/v2/mafken/products/{code}`) are accessible. For full automation, consider Playwright/Selenium or reverse-engineering the Next.js API routes.
3. ~~**Naivas** — Harden the parser: add JSON-LD / meta-tag extraction (already in generic fallback) as primary strategy; validate against multiple product pages.~~ **Already working** — Naivas parser extracts title from `div.text-xl` and price from `div.product-price`. Verified: live pages return correct title and price (e.g., Brookside Fresh Milk 1L = KES 135).
4. **Backend integration** — Build a `update_prices` management command that maps scraped `{title, price, currency}` to existing `Product` records and upserts `ProductPrice` with `source_url`.

### Backend

5. **PostgreSQL migration** — Set `DB_HOST` and related vars in `.env`; run migrations against PostgreSQL before deployment.
6. **Register test** — Use a stronger password (e.g. `Secret123!`) in `users/tests.py` to satisfy Django validators.
7. **Remove `test_register.py`** from the backend root or move it to a `scripts/` folder so Django's test runner does not import it.

### Frontend

8. **Lint cleanup** — Guard `BuildContext` usage after async gaps; remove unused `_initialized` field.
9. **Basket persistence** — Currently creates a new basket on every app launch; persist basket ID locally for returning users.

---

## How to Run Locally

### Prerequisites

- Python 3.10+ with virtual environment
- Flutter SDK 3.5+
- (Optional) PostgreSQL for production database

### Step 1: Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

API available at `http://127.0.0.1:8000/api/`.

To use PostgreSQL, create a `.env` file in `backend/`:
```
DB_HOST=localhost
DB_NAME=savebasket
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432
SECRET_KEY=your-secret-key
DEBUG=True
```

### Step 2: Frontend

```bash
cd frontend
flutter pub get
flutter run
```

Supports Android, iOS, Chrome/Web, and Desktop. Ensure the backend is running first; log in or register to access basket features.

### Step 3: Scrapper (standalone)

```bash
cd Scrapper
python -m venv venv
# Windows:
venv\Scripts\activate
pip install -r requirements.txt

python run_scraper.py "https://naivas.online/<product-page-url>"
```

Only scrape sites you have permission to access. Respect each site's terms of service and rate limits.

---

## Architecture Summary

SaveBasket follows a classic three-tier pattern:

1. **Data layer** — Django ORM models (`Supermarket`, `Branch`, `Product`, `ProductPrice`, `Basket`, `BasketItem`) with SQLite/PostgreSQL
2. **API layer** — Django REST Framework viewsets with JWT authentication and CORS for the Flutter client
3. **Presentation layer** — Flutter app with Provider state management, responsive Material 3 UI, and platform-aware API routing

The scraper is a fourth, independent ingestion pipeline planned to replace static seeded prices with live supermarket data once Quickmart and Carrefour parsers are fixed and a backend sync command is implemented.
