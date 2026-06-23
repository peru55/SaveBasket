"""Ethical web scraper with robots.txt compliance and polite delays."""

import json
import logging
import re
import threading
import time
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
import requests_cache
from bs4 import BeautifulSoup
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from naivas import parse_naivas
from quickmart import parse_quickmart
from carrefour import parse_carrefour
from cleanshelf import parse_cleanshelf
from product import source_from_domain, validate_product

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    cloudscraper = None
    HAS_CLOUDSCRAPER = False

logger = logging.getLogger("ethical_scraper")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

SITE_PARSERS = (
    ("naivas.online", "Naivas", parse_naivas),
    ("quickmart.co.ke", "Quickmart", parse_quickmart),
    ("carrefour.ke", "Carrefour", parse_carrefour),
    ("cleanshelf.online", "CleanShelf", parse_cleanshelf),
)

# Matches Kenyan price formats: 135, 135.00, 1,350, 1,350.00, 1500, 1500.00
MONEY_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


class EthicalScraper:
    def __init__(
        self,
        cache_name="scraper_cache",
        expire_after=300,
        default_delay=1.0,
        user_agent=None,
        quickmart_location=None,
    ):
        self.session = requests_cache.CachedSession(cache_name, expire_after=expire_after)
        self.user_agent = user_agent or BROWSER_UA
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Language": "en-KE,en;q=0.9",
            }
        )
        self.robots: dict[str, RobotFileParser | None] = {}
        self.last_request_time: dict[str, float] = {}
        self.default_delay = default_delay
        self.lock = threading.Lock()
        self._quickmart_location_ready = False
        self.quickmart_location = quickmart_location or {
            "address": "Nairobi, Kenya",
            "lat": "-1.286389",
            "lng": "36.817223",
            "radius": "15",
        }
        self.domain_timeouts = {
            "quickmart.co.ke": 60,
            "carrefour.ke": 60,
            "naivas.online": 30,
            "cleanshelf.online": 30,
            "api.cleanshelf.online": 30,
        }
        self.default_timeout = 15

    @staticmethod
    def _base_domain(url: str) -> str:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain

    @staticmethod
    def _parse_money(text: str | None) -> float | None:
        """Parse a Kenyan price string to float.

        Handles formats: 135, 135.00, 1,350, 1,350.00, KES 135, KSh 135.
        Commas are thousands separators, the last dot is the decimal point.
        """
        if not text:
            return None
        # Normalize non-breaking spaces
        cleaned = text.replace("\xa0", " ").replace("KES", "").replace("KSh", "").replace("ksh", "").strip()
        match = MONEY_RE.search(cleaned)
        if not match:
            return None
        raw = match.group(0)
        # Remove thousands separators (commas)
        raw = raw.replace(",", "")
        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def _meta_content(soup: BeautifulSoup, prop: str) -> str | None:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return tag.get("content") if tag else None

    def _normalize_fetch_url(self, url: str) -> str:
        parsed = urlparse(url)
        domain = self._base_domain(url)

        if "naivas.online" in domain:
            path = parsed.path
            if path.endswith(".html"):
                path = path[: -len(".html")]
            netloc = parsed.netloc or "www.naivas.online"
            if not netloc.startswith("www."):
                netloc = f"www.{netloc}"
            return urlunparse((parsed.scheme or "https", netloc, path, "", parsed.query, ""))

        if "quickmart.co.ke" in domain and parsed.path.startswith("/product/"):
            # Legacy guessed paths are invalid on Growcer storefront.
            slug = parsed.path.rsplit("/", 1)[-1].replace("_", "-")
            return urlunparse((parsed.scheme or "https", parsed.netloc, f"/{slug}", "", "", ""))

        if "cleanshelf.online" in domain:
            netloc = parsed.netloc
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return urlunparse((parsed.scheme or "https", netloc, parsed.path or "/", "", parsed.query, ""))

        return url

    def can_fetch(self, url: str) -> bool:
        domain = urlparse(url).netloc
        if domain not in self.robots:
            rp = RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            try:
                resp = self.session.get(robots_url, timeout=5)
                if resp.status_code == 200 and resp.text:
                    rp.parse(resp.text.splitlines())
                else:
                    logger.info(
                        "No robots.txt (status %s) for %s — allowing fetch by default",
                        resp.status_code,
                        domain,
                    )
                    self.robots[domain] = None
                    return True
            except requests.RequestException:
                logger.warning("Could not retrieve robots.txt for %s — allowing fetch by default", domain)
                self.robots[domain] = None
                return True
            self.robots[domain] = rp

        rp = self.robots.get(domain)
        if rp is None:
            return True
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            logger.warning("robots.txt parse error for %s — allowing fetch by default", domain)
            return True

    def _wait_for_delay(self, domain: str):
        with self.lock:
            last = self.last_request_time.get(domain, 0)
            elapsed = time.time() - last
            if elapsed < self.default_delay:
                time.sleep(self.default_delay - elapsed)
            self.last_request_time[domain] = time.time()

    def _ensure_quickmart_location(self):
        if self._quickmart_location_ready:
            return
        home = "https://www.quickmart.co.ke/"
        self.session.get(home, timeout=self.domain_timeouts["quickmart.co.ke"])
        geo_url = "https://www.quickmart.co.ke/geo-location/set-up-user-location"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": home,
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        resp = self.session.post(geo_url, data=self.quickmart_location, headers=headers, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != 1:
            raise RuntimeError(f"Quickmart location setup failed: {payload.get('msg', payload)}")
        self._quickmart_location_ready = True
        logger.info("Quickmart delivery location set for %s", self.quickmart_location["address"])

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=15),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch(self, url: str, timeout: int | None = None) -> str:
        url = self._normalize_fetch_url(url)
        if not self.can_fetch(url):
            logger.warning("robots.txt disallows fetching %s", url)
            raise PermissionError(f"Fetching disallowed by robots.txt: {url}")

        domain = self._base_domain(url)
        if "quickmart.co.ke" in domain:
            self._ensure_quickmart_location()

        self._wait_for_delay(urlparse(url).netloc)
        if timeout is None:
            timeout = self.domain_timeouts.get(domain, self.default_timeout)

        headers = {}
        if "carrefour.ke" in domain:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.carrefour.ke/",
            }

        logger.debug("Fetching %s with timeout %ds", url, timeout)
        if "carrefour.ke" in domain:
            # Carrefour's Akamai edge can return a 53-byte empty shell with HTTP 200.
            # Never cache that response, or later runs will keep reusing the block page.
            with self.session.cache_disabled():
                resp = self.session.get(url, timeout=timeout, headers=headers or None)
        else:
            resp = self.session.get(url, timeout=timeout, headers=headers or None)
        resp.raise_for_status()
        if getattr(resp, "from_cache", False):
            logger.info("Cache hit for %s", url)
        else:
            logger.info("Fetched %s — status %s", url, resp.status_code)

        # Detect CDN block pages (empty shell or access denied)
        if "carrefour.ke" in domain and (
            self._looks_like_empty_shell(resp.text) or "access denied" in resp.text[:300].lower()
        ):
            logger.warning(
                "CDN block detected for %s (%d bytes) — trying cloudscraper fallback",
                url,
                len(resp.text),
            )
            if HAS_CLOUDSCRAPER:
                cs = cloudscraper.create_scraper()
                try:
                    cs_resp = cs.get(url, timeout=timeout)
                    cs_text = cs_resp.text
                    # cloudscraper succeeded if we got real HTML (not blocked)
                    if not self._looks_like_empty_shell(cs_text) and "access denied" not in cs_text[:300].lower():
                        logger.info("cloudscraper fallback succeeded for %s", url)
                        return cs_text
                    logger.warning(
                        "cloudscraper fallback still blocked for %s: status=%s bytes=%d",
                        url,
                        getattr(cs_resp, "status_code", None),
                        len(cs_text),
                    )
                except Exception as cs_err:
                    logger.warning("cloudscraper fallback also failed: %s", cs_err)

        return resp.text

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=15),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch_json(self, url: str, timeout: int | None = None, headers: dict | None = None) -> dict:
        domain = self._base_domain(url)
        self._wait_for_delay(urlparse(url).netloc)
        if timeout is None:
            timeout = self.domain_timeouts.get(domain, self.default_timeout)

        merged = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.carrefour.ke/",
        }
        if headers:
            merged.update(headers)

        # Use cloudscraper for carrefour JSON endpoints if available
        if HAS_CLOUDSCRAPER and "carrefour.ke" in domain:
            cs = cloudscraper.create_scraper()
            try:
                cs_resp = cs.get(url, timeout=timeout, headers=merged)
                cs_resp.raise_for_status()
                payload = cs_resp.json()
                if not isinstance(payload, dict):
                    raise ValueError(f"Expected JSON object from {url}")
                return payload
            except Exception as cs_err:
                logger.warning("cloudscraper fetch_json failed for %s, falling back: %s", url, cs_err)

        if "carrefour.ke" in domain:
            with self.session.cache_disabled():
                resp = self.session.get(url, timeout=timeout, headers=merged)
        else:
            resp = self.session.get(url, timeout=timeout, headers=merged)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object from {url}")
        return payload

    def parse_prices(self, html: str, selector: str | None = None) -> list[float]:
        """Parse price values from HTML. Uses thousands-aware parsing."""
        soup = BeautifulSoup(html, "lxml")
        if selector:
            texts = [e.get_text(" ", strip=True) for e in soup.select(selector)]
        else:
            texts = [s.get_text(" ", strip=True) for s in soup.find_all(string=True)]

        prices = []
        for text in texts:
            for match in MONEY_RE.findall(text):
                # Remove thousands commas, keep decimal dot
                normalized = match.replace(",", "")
                try:
                    prices.append(float(normalized))
                except ValueError:
                    continue
        return prices

    def _extract_json_ld(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "null")
            except json.JSONDecodeError:
                continue
            queue = data if isinstance(data, list) else [data]
            while queue:
                item = queue.pop(0)
                if not isinstance(item, dict):
                    continue
                if "@graph" in item and isinstance(item["@graph"], list):
                    queue.extend(item["@graph"])
                results.append(item)
        return results

    def _product_from_json_ld(self, html: str) -> dict | None:
        """Extract product info from JSON-LD, handling various price structures."""
        for obj in self._extract_json_ld(html):
            obj_type = str(obj.get("@type", "")).lower()
            if "product" not in obj_type:
                continue

            offers = obj.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            offer_list = offers.get("offers")
            if isinstance(offer_list, list) and offer_list:
                # Multiple offers: take the first one
                offers = offer_list[0]

            price = None
            currency = offers.get("priceCurrency") or "KES"

            # Direct price field
            if offers.get("price") is not None:
                price = offers["price"]
            # PriceSpecification sub-object
            elif isinstance(offers.get("priceSpecification"), dict):
                price = offers["priceSpecification"].get("price")
            # LowPrice / HighPrice range
            elif offers.get("lowPrice") is not None:
                price = offers["lowPrice"]
            # Price in the aggregateRating or similar alternate location
            elif isinstance(offers.get("priceSpecification"), dict):
                price = offers["priceSpecification"].get("price")
            # Check obj level directly
            elif obj.get("offers") and isinstance(obj.get("offers"), dict):
                price = obj["offers"].get("price") or (obj["offers"].get("priceSpecification") or {}).get("price")

            # Try alternate field: "price" at product level
            if price is None and obj.get("price") is not None:
                price = obj["price"]

            price_val = self._parse_money(str(price)) if price is not None else None
            if price_val is not None:
                return {
                    "title": obj.get("name"),
                    "price": price_val,
                    "currency": currency,
                }
        return None

    def _generic_price_from_html(self, html: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        json_ld = self._product_from_json_ld(html)
        if json_ld:
            logger.info("JSON-LD product detected: %s", json_ld)
            return json_ld

        og_title = self._meta_content(soup, "og:title") or self._meta_content(soup, "twitter:title")
        og_price = self._meta_content(soup, "product:price:amount") or self._meta_content(soup, "og:price:amount")
        og_currency = self._meta_content(soup, "product:price:currency") or self._meta_content(soup, "og:price:currency")
        price_val = self._parse_money(og_price)
        if price_val is not None:
            return {
                "title": og_title,
                "price": price_val,
                "currency": og_currency or "KES",
                "image_url": self._meta_content(soup, "og:image") or self._meta_content(soup, "twitter:image"),
                "category": self._category_from_html(soup),
                "availability": self._availability_from_html(soup),
            }

        price_candidates = [
            el
            for el in soup.select("[class*=price], [id*=price], .product-price, .price--main, .offer-price, [class*=Price], [class*=amount]")
            if not self._is_in_excluded(el)
        ]
        title_candidates = [
            el
            for el in soup.select("[class*=title], [class*=name], h1, .product-name, .productTitle, [class*=Title], [class*=Name]")
            if not self._is_in_excluded(el)
        ]

        price_text = next((el.get_text(" ", strip=True) for el in price_candidates if el.get_text(strip=True)), None)
        title_text = None
        for el in title_candidates:
            text = el.get_text(" ", strip=True)
            if text and not self._looks_like_age_prompt(text):
                title_text = text
                break

        return {
            "title": title_text or og_title,
            "price": self._parse_money(price_text),
            "currency": "KES" if price_text else None,
            "image_url": self._meta_content(soup, "og:image") or self._meta_content(soup, "twitter:image"),
            "category": self._category_from_html(soup),
            "availability": self._availability_from_html(soup),
        }

    def _is_in_excluded(self, el) -> bool:
        exclude_keywords = ["modal", "overlay", "age", "cookie", "consent", "popup", "dialog", "intro", "legal", "banner", "toast"]
        for parent in el.parents:
            if not getattr(parent, "attrs", None):
                continue
            classes = parent.get("class") or []
            ids = [parent.get("id")] if parent.get("id") else []
            combined = " ".join(classes + ids).lower()
            if any(keyword in combined for keyword in exclude_keywords):
                return True
        return False

    def _looks_like_age_prompt(self, text: str) -> bool:
        return bool(re.search(r"over\s*18|confirm.*18|are you.*over|please confirm", text, re.I))

    def _availability_from_html(self, soup: BeautifulSoup) -> str:
        text = soup.get_text(" ", strip=True).lower()
        if re.search(r"\bout\s+of\s+stock\b|sold\s+out|unavailable", text):
            return "out_of_stock"
        if re.search(r"\bin\s+stock\b|add\s+to\s+cart|available", text):
            return "in_stock"
        return "unknown"

    def _category_from_html(self, soup: BeautifulSoup) -> str | None:
        for prop in ("product:category", "category", "article:section"):
            category = self._meta_content(soup, prop)
            if category:
                return category.strip()
        crumbs = [
            el.get_text(" ", strip=True)
            for el in soup.select("[class*=breadcrumb] a, nav[aria-label*=breadcrumb] a")
            if el.get_text(strip=True)
        ]
        return crumbs[-1] if crumbs else None

    @staticmethod
    def _looks_like_empty_shell(html: str) -> bool:
        stripped = html.strip()
        return len(stripped) < 200 or "<p></p>" in stripped

    def parse_site(self, url: str, html: str) -> dict:
        """Dispatch to the appropriate supermarket parser based on domain."""
        domain = self._base_domain(url)
        source = source_from_domain(domain)
        try:
            parser = None
            for parser_domain, parser_source, parser_func in SITE_PARSERS:
                if parser_domain in domain:
                    source = parser_source
                    parser = parser_func
                    break
            if parser:
                logger.info("Dispatching to %s parser for %s", source, domain)
                raw = parser(self, url, html)
            else:
                raw = self._generic_price_from_html(html)
        except Exception as exc:
            logger.exception("Parser failed for %s", url)
            raw = {"title": None, "price": None, "currency": None, "error": str(exc)}
        raw = self._enrich_product(raw, html)
        return validate_product(raw, source=source, url=url)

    def scrape_product(self, url: str) -> dict:
        """Fetch, parse, and validate one product URL."""
        html = self.fetch(url)
        return self.parse_site(url, html)

    def _enrich_product(self, raw: dict | None, html: str) -> dict:
        raw = dict(raw or {})
        soup = BeautifulSoup(html, "lxml")
        raw.setdefault(
            "image_url",
            self._meta_content(soup, "og:image") or self._meta_content(soup, "twitter:image"),
        )
        raw.setdefault("category", self._category_from_html(soup))
        raw.setdefault("availability", self._availability_from_html(soup))
        return raw


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scraper.py <url>")
        raise SystemExit(1)

    scraper = EthicalScraper()
    page_url = sys.argv[1]
    page_html = scraper.fetch(page_url)
    parsed = scraper.parse_site(page_url, page_html)
    print(parsed)
