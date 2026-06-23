"""Carrefour-specific parser for SaveBasket."""

import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger("ethical_scraper.carrefour")

# Check if Playwright is available for browser-based fallback
try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.info("Playwright not available — browser fallback for Carrefour disabled")


def carrefour_product_code(url: str) -> str | None:
    """Extract Carrefour product code from URL path (/p/{code})."""
    match = re.search(r"/p/(\d+)", urlparse(url).path)
    return match.group(1) if match else None


def _fetch_with_playwright(url: str, timeout_ms: int = 30000) -> str | None:
    """Fetch page HTML using Playwright headless browser.

    Some sites (like Carrefour) use aggressive CDN protection that blocks
    regular requests. A headless browser provides real browser fingerprints
    which can bypass these blocks.
    """
    if not HAS_PLAYWRIGHT:
        return None
    try:
        with sync_playwright() as p:
            # Use chromium with some stealth-like settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-KE",
                timezone_id="Africa/Nairobi",
                viewport={"width": 1920, "height": 1080},
                # Disable WebRTC to prevent IP leaks
                permissions=[],
                # Allow cookies
                no_viewport=False,
            )
            page = context.new_page()
            # Add some stealth headers
            page.set_extra_http_headers({
                "Accept-Language": "en-KE,en;q=0.9,sw;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            })
            # Try with 'load' instead of 'networkidle' which can hang
            page.goto(url, wait_until="load", timeout=timeout_ms)
            # Wait a bit for dynamic content
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()

            if html and len(html.strip()) > 200:
                logger.info(
                    "Playwright fetch succeeded for %s (%d chars)", url, len(html)
                )
                return html
            else:
                logger.warning(
                    "Playwright fetch returned empty/shell for %s", url
                )
                return None
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return None


def _fetch_with_playwright_occ(
    product_code: str, timeout_ms: int = 30000
) -> dict | None:
    """Fetch Carrefour product data using Playwright to hit the OCC API."""
    api_url = (
        "https://www.carrefour.ke/occ/v2/mafken/products/"
        f"{product_code}?fields=code,name,price(formattedValue,value,currencyIso)"
    )
    if not HAS_PLAYWRIGHT:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-KE",
            )
            page = context.new_page()

            # First visit the homepage to set cookies/session
            try:
                page.goto(
                    "https://www.carrefour.ke/",
                    wait_until="load",
                    timeout=20000,
                )
            except Exception:
                pass

            # Now try the OCC API via browser
            response = page.goto(
                api_url, wait_until="load", timeout=timeout_ms
            )
            if response:
                body = response.json()
                browser.close()
                if body and body.get("code"):
                    logger.info(
                        "Playwright OCC fetch succeeded for product %s",
                        product_code,
                    )
                    return body

            browser.close()
            return None
    except Exception as exc:
        logger.warning(
            "Playwright OCC fetch failed for %s: %s", product_code, exc
        )
        return None


def parse_carrefour(scraper, url: str, html: str) -> dict:
    """Parse a Carrefour product page (Next.js storefront with CDN protection).

    Falls back to Playwright headless browser if standard requests are CDN-blocked.
    """
    code = carrefour_product_code(url)

    # Detect CDN block pages (both empty shells and access denied)
    is_blocked = (
        scraper._looks_like_empty_shell(html)
        or "access denied" in html[:200].lower()
    )

    # Strategy 1: If blocked, try OCC API via standard requests
    if code and is_blocked:
        api_result = carrefour_from_occ(scraper, code, referer=url)
        if api_result.get("price") is not None:
            return api_result

    # Strategy 2: Try Playwright browser fallback to fetch real HTML
    if is_blocked and HAS_PLAYWRIGHT:
        logger.info("Attempting Playwright browser fallback for %s", url)
        pw_html = _fetch_with_playwright(url)
        if pw_html:
            # Re-parse with the real HTML from browser
            generic = scraper._generic_price_from_html(pw_html)
            if generic.get("price") is not None:
                return generic

            # Also try code-based parsing on the real HTML
            soup = BeautifulSoup(pw_html, "lxml")
            title = soup.find("h1")
            price_match = re.search(
                r"(?:KES|KSh|ksh)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
                pw_html,
                re.I,
            )
            if title and price_match:
                raw_price = price_match.group(1).replace(",", "")
                try:
                    return {
                        "title": title.get_text(strip=True),
                        "price": float(raw_price),
                        "currency": "KES",
                    }
                except ValueError:
                    pass

            # Try JSON-LD in the fetched HTML
            json_ld_result = scraper._product_from_json_ld(pw_html)
            if json_ld_result:
                return json_ld_result

    # Strategy 3: Try OCC API via Playwright if standard OCC also failed
    if code and is_blocked and HAS_PLAYWRIGHT:
        logger.info("Attempting Playwright OCC fallback for product %s", code)
        pw_occ_data = _fetch_with_playwright_occ(code)
        if pw_occ_data:
            price_block = pw_occ_data.get("price") or {}
            value = price_block.get("value")
            if value is None:
                value = scraper._parse_money(
                    price_block.get("formattedValue")
                )
            price_val = (
                scraper._parse_money(str(value))
                if value is not None
                else None
            )
            if price_val is not None:
                result = {
                    "title": pw_occ_data.get("name"),
                    "price": price_val,
                    "currency": price_block.get("currencyIso") or "KES",
                }
                logger.info(
                    "Carrefour Playwright OCC product detected: %s", result
                )
                return result

    # Strategy 4: Try parsing whatever HTML we have
    generic = scraper._generic_price_from_html(html)
    if generic.get("price") is not None:
        return generic

    # Strategy 5: If still blocked, give clear error
    if is_blocked and code:
        return {
            "title": None,
            "price": None,
            "currency": None,
            "error": (
                "Carrefour blocked this scraper client at the CDN edge. "
                "Requests returned the 53-byte empty Akamai shell, and browser/API "
                "fallbacks did not return product data. This can happen even on a "
                "Kenyan network when Akamai rejects the client fingerprint or route. "
                "Try a normal browser session with exported cookies, a different ISP/VPN "
                "route, or a legitimate product/feed API source."
            ),
        }

    # Non-blocked page with partial HTML
    if len(html) > 200:
        soup = BeautifulSoup(html, "lxml")
        title = soup.find("h1")
        # Improved pattern: KES 1,234 or KES1234 or KSh 1,234.56
        price_match = re.search(
            r"(?:KES|KSh|ksh)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", html, re.I
        )
        if title and price_match:
            raw_price = price_match.group(1).replace(",", "")
            try:
                return {
                    "title": title.get_text(strip=True),
                    "price": float(raw_price),
                    "currency": "KES",
                }
            except ValueError:
                pass

        # Try matching just numbers near "KES" context
        price_match_2 = re.search(
            r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:KES|KSh)", html, re.I
        )
        if title and price_match_2:
            raw_price = price_match_2.group(1).replace(",", "")
            try:
                return {
                    "title": title.get_text(strip=True),
                    "price": float(raw_price),
                    "currency": "KES",
                }
            except ValueError:
                pass

        # Try JSON-LD embedded in script tags (Next.js often inlines this)
        json_ld_result = scraper._product_from_json_ld(html)
        if json_ld_result:
            return json_ld_result

        # Try finding price in script __NEXT_DATA__ or similar
        for script in soup.find_all("script"):
            if script.string and "price" in script.string.lower():
                next_match = re.search(
                    r'"price"\s*:\s*"?(\d+(?:\.\d+)?)"?', script.string
                )
                if next_match:
                    try:
                        price = float(next_match.group(1))
                        return {
                            "title": title.get_text(strip=True)
                            if title
                            else None,
                            "price": price,
                            "currency": "KES",
                        }
                    except ValueError:
                        pass

    return scraper._generic_price_from_html(html)


def carrefour_from_occ(scraper, product_code: str, referer: str) -> dict:
    """Fetch product data from Carrefour's OCC API endpoint."""
    api_url = (
        "https://www.carrefour.ke/occ/v2/mafken/products/"
        f"{product_code}?fields=code,name,price(formattedValue,value,currencyIso)"
        "&lang=en&curr=KES"
    )
    try:
        # Use cloudscraper-enabled fetch to warm up the session
        scraper.fetch("https://www.carrefour.ke/")
        # cloudscraper fetch_json fallback is now built into fetch_json
        payload = scraper.fetch_json(
            api_url,
            headers={
                "Referer": referer,
                "Origin": "https://www.carrefour.ke",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
        )
    except Exception as exc:
        logger.warning("Carrefour OCC request failed: %s", exc)
        return {"title": None, "price": None, "currency": None}

    price_block = payload.get("price") or {}
    value = price_block.get("value")
    if value is None:
        value = scraper._parse_money(price_block.get("formattedValue"))
    price_val = scraper._parse_money(str(value)) if value is not None else None
    if price_val is None:
        return {"title": payload.get("name"), "price": None, "currency": None}

    result = {
        "title": payload.get("name"),
        "price": price_val,
        "currency": price_block.get("currencyIso") or "KES",
    }
    logger.info("Carrefour OCC product detected: %s", result)
    return result
