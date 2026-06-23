"""Naivas-specific parser for SaveBasket."""

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("ethical_scraper.naivas")


def parse_naivas(scraper, url: str, html: str) -> dict:
    """Parse a Naivas product page.

    Naivas URLs like /brookside-dairy-best-milk-500ml often return search/listing
    pages with multiple products. The correct product card is identified by matching
    its anchor href against the original URL's slug, then extracting the price from
    that specific card.
    """
    soup = BeautifulSoup(html, "lxml")

    # Get the page-level title
    title = scraper._meta_content(soup, "og:title") or scraper._meta_content(
        soup, "twitter:title"
    )

    title_div = soup.select_one("div.text-xl.mb-1") or soup.select_one("div.text-xl")
    if title_div:
        candidate_title = title_div.get_text(strip=True)
        if candidate_title and not scraper._looks_like_age_prompt(candidate_title):
            title = candidate_title

    price = None

    # Strategy 1: Find product card whose link matches the URL slug
    # Naivas listing pages have cards with class "border border-naivas-bg"
    # Each card contains an <a> with href pointing to the product page.
    # The title is at page-level, NOT inside the cards, so we match by URL.
    slug = urlparse(url).path.strip("/").split("/")[-1]
    slug_clean = slug.replace("-", " ").lower().strip()

    product_cards = soup.select("div.border.border-naivas-bg")
    target_card = None

    for card in product_cards:
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href", "")
        # Check if the href contains the slug (matching by URL identity)
        if slug in href:
            target_card = card
            logger.debug("Naivas found matching card by href: %s", href)
            break
        # Also check if href contains the path segment
        path_slug = urlparse(url).path.strip("/")
        if path_slug in href:
            target_card = card
            logger.debug("Naivas found matching card by path: %s", href)
            break

    if target_card:
        price_el = target_card.select_one(
            "div.product-price span.font-bold, div.product-price"
        )
        if price_el:
            price = scraper._parse_money(price_el.get_text(" ", strip=True))
        if price is not None:
            logger.info(
                "Naivas parser (card by href): title=%s price=%s",
                title,
                price,
            )
            return {"title": title, "price": price, "currency": "KES"}

    # Strategy 2: Walk up from title to find nearest product-price
    if price is None and title_div:
        candidate = title_div
        for depth in range(5):
            if candidate is None:
                break
            price_el = candidate.select_one(
                "div.product-price span.font-bold, div.product-price"
            )
            if price_el:
                price = scraper._parse_money(price_el.get_text(" ", strip=True))
                if price is not None:
                    logger.debug("Naivas price found near title: %s", price)
                    break
            candidate = candidate.parent

    # Strategy 3: Direct selectors for Naivas product detail page
    if price is None:
        for selector in [
            "div.product-full-details div.product-price",
            "div.product-price span.font-bold",
            "div.product-price",
            "[class*=product-price]",
            ".price",
            "[class*=price]",
        ]:
            for price_el in soup.select(selector):
                if scraper._is_in_excluded(price_el):
                    continue
                price = scraper._parse_money(price_el.get_text(" ", strip=True))
                if price is not None:
                    break
            if price is not None:
                break

    # Strategy 4: Regex on body text
    if price is None:
        body_text = soup.get_text(" ", strip=True)
        kes_matches = re.findall(
            r"(?:KES|KSh|ksh)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", body_text
        )
        if kes_matches:
            price = scraper._parse_money(kes_matches[0])

    if title and price is not None:
        logger.info("Naivas parser: title=%s price=%s", title, price)
        return {"title": title, "price": price, "currency": "KES"}

    # Strategy 5: Search fallback
    if slug_clean:
        search_result = naivas_search_fallback(scraper, slug_clean)
        if search_result.get("price") is not None:
            return search_result

    return scraper._generic_price_from_html(html)


def naivas_search_fallback(scraper, query: str) -> dict:
    """Fallback search on Naivas site when direct page parsing fails."""
    if not query:
        return {"title": None, "price": None, "currency": None}
    search_url = f"https://www.naivas.online/search?query={requests.utils.quote(query)}"
    try:
        html = scraper.fetch(search_url)
    except Exception as exc:
        logger.warning("Naivas search fallback failed: %s", exc)
        return {"title": None, "price": None, "currency": None}

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.border.border-naivas-bg")
    best = None
    query_tokens = set(query.lower().split())
    for card in cards:
        link = card.find("a", href=True)
        if not link:
            continue
        card_title = link.get_text(" ", strip=True)
        if not card_title:
            continue
        overlap = sum(1 for token in query_tokens if token in card_title.lower())
        if overlap == 0:
            continue
        price_el = card.select_one("div.product-price")
        price = scraper._parse_money(price_el.get_text(" ", strip=True) if price_el else None)
        if price is None:
            continue
        candidate = {
            "title": card_title,
            "price": price,
            "currency": "KES",
            "url": link["href"],
        }
        if best is None or overlap > best["score"]:
            best = {**candidate, "score": overlap}

    if best:
        logger.info("Naivas search fallback match: %s", best)
        return {k: best[k] for k in ("title", "price", "currency")}
    return {"title": None, "price": None, "currency": None}