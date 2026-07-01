"""Naivas-specific parser for SaveBasket."""

import json
import logging
import re
import html as html_lib
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("ethical_scraper.naivas")


def _requested_slug(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[-1].lower()


def _card_href_slug(href: str) -> str:
    return urlparse(href).path.strip("/").split("/")[-1].lower()


def _price_from_card(scraper, card):
    price_el = card.select_one("div.product-price span.font-bold, div.product-price")
    if not price_el:
        return None
    return scraper._parse_money(price_el.get_text(" ", strip=True))


def _title_from_card(card) -> str | None:
    link = card.find("a", href=True)
    if not link:
        return None
    return (
        link.get("title")
        or link.get("aria-label")
        or link.get_text(" ", strip=True)
        or None
    )


def _product_json_ld(scraper, soup) -> dict:
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(html_lib.unescape(raw))
        except json.JSONDecodeError:
            continue

        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict) or item.get("@type") != "Product":
                continue
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price") if isinstance(offers, dict) else None
            parsed_price = scraper._parse_money(str(price)) if price is not None else None
            if parsed_price is not None:
                return {
                    "title": item.get("name"),
                    "price": parsed_price,
                    "currency": offers.get("priceCurrency") if isinstance(offers, dict) else "KES",
                }
    return {"title": None, "price": None, "currency": None}


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
    slug = _requested_slug(url)
    slug_clean = slug.replace("-", " ").lower().strip()

    product_cards = soup.select("div.border.border-naivas-bg")
    target_card = None

    for card in product_cards:
        link = card.find("a", href=True)
        if not link:
            continue
        href = link.get("href", "")
        href_slug = _card_href_slug(href)
        if href_slug == slug:
            target_card = card
            logger.debug("Naivas found matching card by href: %s", href)
            break

    if target_card:
        price = _price_from_card(scraper, target_card)
        if price is not None:
            card_title = _title_from_card(target_card)
            logger.info(
                "Naivas parser (card by href): title=%s price=%s",
                card_title or title,
                price,
            )
            return {"title": card_title or title, "price": price, "currency": "KES"}

    structured = _product_json_ld(scraper, soup)
    if structured.get("price") is not None:
        logger.info(
            "Naivas parser (json-ld offer): title=%s price=%s",
            structured.get("title") or title,
            structured["price"],
        )
        return {
            "title": structured.get("title") or title,
            "price": structured["price"],
            "currency": structured.get("currency") or "KES",
        }

    if product_cards:
        logger.warning(
            "Naivas listing page did not contain requested slug '%s'; refusing broad price fallback",
            slug,
        )
        search_result = naivas_search_fallback(scraper, slug_clean, expected_slug=slug)
        if search_result.get("price") is not None:
            return search_result
        return {"title": title, "price": None, "currency": "KES"}

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


def naivas_search_fallback(scraper, query: str, expected_slug: str | None = None) -> dict:
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
        if expected_slug and _card_href_slug(link["href"]) != expected_slug:
            continue
        card_title = link.get_text(" ", strip=True)
        card_title = card_title or link.get("title") or link.get("aria-label")
        if not card_title:
            continue
        overlap = sum(1 for token in query_tokens if token in card_title.lower())
        if overlap == 0:
            continue
        price = _price_from_card(scraper, card)
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
