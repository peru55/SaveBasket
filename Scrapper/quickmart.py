"""Quickmart-specific parser for SaveBasket."""

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("ethical_scraper.quickmart")


def parse_quickmart(scraper, url: str, html: str) -> dict:
    """Parse a Quickmart product page (Growcer storefront).

    Quickmart URLs like /brookside-uht-fino-carton-500ml-36 often return
    listing pages with multiple products. The correct product card is identified
    by matching its anchor href against the original URL's slug, then extracting
    the price from the span.products-price-new element in that card.
    """
    soup = BeautifulSoup(html, "lxml")
    title = scraper._meta_content(soup, "og:title") or scraper._meta_content(soup, "twitter:title")
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)

    price = None

    # Strategy 1: If the page is a product detail page (has div.product-description),
    # extract price directly from the page's price element — no href matching needed.
    # If it's a listing page (multiple product cards), use href matching to find the
    # correct product card by slug.
    slug = urlparse(url).path.strip("/")

    # Check if this is a detail page (single product)
    detail_container = soup.select_one("div.product-description")
    if detail_container:
        # Detail page: extract price from within the product-description container
        price_el = detail_container.select_one(
            "span.products-price-new, div.products-price, span.product__price"
        )
        if price_el:
            price = scraper._parse_money(price_el.get_text(" ", strip=True))
        if price is not None and title:
            logger.debug("Quickmart price from detail page: %s", price)
            return {"title": title, "price": price, "currency": "KES"}
    else:
        # Listing page: find product card by matching href slug
        # First try exact match (slug in href) for listing page product cards
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip("/")
            if not href:
                continue
            if slug in href:
                in_product = bool(
                    anchor.get("title")
                    or anchor.find_parent(class_=lambda c: c and "product" in str(c).lower() if c else False)
                )
                text = anchor.get_text(strip=True)
                if in_product or (text and len(text) > 3):
                    card_container = anchor.parent
                    for _ in range(10):
                        if card_container is None:
                            break
                        price_el = card_container.select_one(
                            "span.products-price-new, div.products-price, span.product__price"
                        )
                        if price_el:
                            text = price_el.get_text(" ", strip=True)
                            price = scraper._parse_money(text)
                            if price is not None:
                                logger.debug(
                                    "Quickmart price via listing href match: %s", price
                                )
                                break
                        card_container = card_container.parent
                    if price is not None:
                        return {"title": title, "price": price, "currency": "KES"}

    # Strategy 2: Growcer product page with modern class names
    price_selectors = [
        # Modern Growcer classes
        "span.product__price",
        "div.product__price",
        ".product__price",
        "span.price",
        "div.price",
        ".price--large",
        ".price--main",
        ".price-item--regular",
        "span.price-item",
        # Legacy/fallback selectors
        ".products-price-new",
        ".products-price",
        "[class*=products-price]",
        ".product-price",
        ".product-price__value",
        "[class*=product-price]",
        # Generic
        ".price",
        "[class*=price]",
        "[class*=Price]",
    ]

    for selector in price_selectors:
        for el in soup.select(selector):
            if scraper._is_in_excluded(el):
                continue
            text = el.get_text(" ", strip=True)
            price = scraper._parse_money(text)
            if price is not None:
                logger.debug("Quickmart price found with selector '%s': %s", selector, text)
                break
        if price is not None:
            break

    # Strategy 3: Look for "KES" or "KSh" followed by a number directly
    if price is None:
        body_text = soup.get_text(" ", strip=True)
        kes_matches = re.findall(r'(?:KES|KSh|ksh)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', body_text)
        if kes_matches:
            price = scraper._parse_money(kes_matches[0])

    if title and price is not None:
        logger.info("Quickmart parser: title=%s price=%s", title, price)
        return {"title": title, "price": price, "currency": "KES"}

    parsed = parse_quickmart_search_results(scraper, html)
    if parsed.get("price") is not None:
        return parsed

    if slug and "search" not in slug:
        keyword = slug.rsplit("-", 1)[0].replace("-", " ")
        return quickmart_search(scraper, keyword, prefer=slug)

    return scraper._generic_price_from_html(html)


def parse_quickmart_search_results(scraper, html: str) -> dict:
    """Parse Quickmart search results page for product info."""
    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.find_all("a", title=True):
        title = anchor["title"].strip()
        if not title:
            continue
        href = anchor.get("href") or ""
        if not href.startswith("/") or "quickmart" in title.lower():
            continue
        parent_card = anchor.find_parent(class_=lambda c: c and "product" in c.lower() if c else False)
        if not parent_card:
            continue
        card = anchor
        price = None
        for _ in range(8):
            card = card.parent
            if card is None:
                break
            # Look specifically for price elements rather than full text
            price_el = card.select_one(
                "span.products-price-new, div.products-price, span.product__price"
            )
            if price_el:
                price = scraper._parse_money(price_el.get_text(" ", strip=True))
                if price is not None:
                    break
            # Fallback to full text parsing
            price = scraper._parse_money(card.get_text(" ", strip=True))
            if price is not None:
                break
        if price is not None:
            return {
                "title": title,
                "price": price,
                "currency": "KES",
                "url": anchor.get("href"),
            }
    return {"title": None, "price": None, "currency": None}


def quickmart_search(scraper, keyword: str, prefer: str | None = None) -> dict:
    """Search Quickmart products by keyword."""
    if not keyword or len(keyword.strip()) < 3:
        return {"title": None, "price": None, "currency": None}

    slug = keyword.strip().lower().replace(" ", "-")
    search_url = f"https://www.quickmart.co.ke/products/search/keyword-{slug}/pagesize-30"
    try:
        html = scraper.fetch(search_url)
    except Exception as exc:
        logger.warning("Quickmart search failed: %s", exc)
        return {"title": None, "price": None, "currency": None}

    soup = BeautifulSoup(html, "lxml")
    prefer = (prefer or "").lower()
    best = None
    for anchor in soup.find_all("a", title=True):
        title = anchor["title"].strip()
        href = (anchor.get("href") or "").lower()
        if not title:
            continue
        if not href.startswith("/") or "quickmart" in title.lower():
            continue
        parent_card = anchor.find_parent(class_=lambda c: c and "product" in c.lower() if c else False)
        if not parent_card:
            continue
        card = anchor
        price = None
        for _ in range(8):
            card = card.parent
            if card is None:
                break
            # Look specifically for price elements
            price_el = card.select_one(
                "span.products-price-new, div.products-price, span.product__price"
            )
            if price_el:
                price = scraper._parse_money(price_el.get_text(" ", strip=True))
                if price is not None:
                    break
            # Fallback to full text
            price = scraper._parse_money(card.get_text(" ", strip=True))
            if price is not None:
                break
        if price is None:
            continue
        candidate = {"title": title, "price": price, "currency": "KES", "url": anchor.get("href")}
        if prefer and prefer in href:
            logger.info("Quickmart search exact slug match: %s", candidate)
            return candidate
        if best is None:
            best = candidate

    if best:
        logger.info("Quickmart search best match: %s", best)
    return best or {"title": None, "price": None, "currency": None}