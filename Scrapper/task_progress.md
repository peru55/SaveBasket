# Task Progress: Fix Scraper Issues

## Bugs Found
- [ ] **Naivas**: Wrong price — listing page returns KES 1,349 (another product) instead of KES 58
- [ ] **Quickmart**: Wrong price — listing page returns KES 47 (another product) instead of KES 58
- [ ] **Carrefour**: CDN block — both regular session and cloudscraper return 53-byte empty shell

## Root Causes
1. **Naivas**: `naivas.py` Strategy 1 walks up 8 levels from title, escapes the product card, and grabs a price from another product on the same listing page. All strategies (parent walk, global selectors, regex) pick up the wrong price because the page is a listing page showing many products.
2. **Quickmart**: Same issue — `quickmart.py` price selectors iterate globally over all product cards on the listing page, picking up other products' prices.
3. **Carrefour**: Carrefour's CDN (Akamai/CloudFront) blocks all requests from this IP. Even `cloudscraper` and the OCC API fail because the warm-up fetch to the homepage also gets blocked.

## Fix Plans
- [x] Fix `naivas.py`: Reduce parent walk depth from 8→3 to stay within product card; add title-scoped price search to match the correct product card
- [x] Fix `quickmart.py`: Add title-scoped price search that finds the anchor with matching title text, then extracts price from that specific card
- [ ] Fix `carrefour.py`: Add Playwright headless browser fallback when CDN blocks cloudscraper
- [x] Run tests to verify existing behavior still passes
- [x] Test live sites to confirm fixes work