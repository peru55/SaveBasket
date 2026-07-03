"""EastMatt-specific parser for SaveBasket."""

import logging

from bs4 import BeautifulSoup

logger = logging.getLogger("ethical_scraper.eastmatt")


def _first_price(scraper, soup: BeautifulSoup) -> float | None:
    """Prefer EastMatt/current sale prices before broad price text."""
    selectors = [
        ".detail-info .current-price",
        ".product-detail .current-price",
        ".current-price",
        "p.price ins .woocommerce-Price-amount",
        "p.price ins bdi",
        ".summary ins .woocommerce-Price-amount",
        ".summary ins bdi",
        "p.price .woocommerce-Price-amount",
        "p.price bdi",
        ".summary .woocommerce-Price-amount",
        ".summary [class*=price]",
        ".product .price",
        "[class*=product-price]",
        "[class*=Price]",
        "[class*=price]",
    ]
    for selector in selectors:
        for el in soup.select(selector):
            if scraper._is_in_excluded(el):
                continue
            price = scraper._parse_money(el.get_text(" ", strip=True))
            if price is not None:
                logger.debug("EastMatt price found with selector '%s': %s", selector, price)
                return price
    return None


def _first_text(scraper, soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        for el in soup.select(selector):
            if scraper._is_in_excluded(el):
                continue
            text = el.get_text(" ", strip=True)
            if text and not scraper._looks_like_age_prompt(text):
                return text
    return None


def _first_image(soup: BeautifulSoup) -> str | None:
    for selector in (
        ".product-detail img[src*='itemimages']",
        ".detail-info img[src]",
        "img[src*='itemimages']",
        ".product img[src]",
    ):
        image = soup.select_one(selector)
        if image and image.get("src"):
            return image["src"]
    return None


def parse_eastmatt(scraper, url: str, html: str) -> dict:
    """Parse an EastMatt product page.

    EastMatt currently presents a verification page to simple live requests from
    some networks, so this parser is intentionally built around common
    product-page markup and WooCommerce selectors, with generic extraction as a
    final fallback.
    """
    soup = BeautifulSoup(html, "lxml")

    structured = scraper._product_from_json_ld(html)
    if structured and structured.get("price") is not None:
        return structured

    title = _first_text(
        scraper,
        soup,
        [
            ".detail-info .title-detail",
            ".product-detail .title-detail",
            "h2.title-detail",
            "h1.product_title",
            ".product_title",
            "h1.entry-title",
            ".summary h1",
            "h1",
        ],
    )
    title = title or scraper._meta_content(soup, "og:title") or scraper._meta_content(soup, "twitter:title")

    price = _first_price(scraper, soup)
    if title and price is not None:
        return {
            "name": title,
            "title": title,
            "price": price,
            "currency": "KES",
            "image_url": (
                scraper._meta_content(soup, "og:image")
                or scraper._meta_content(soup, "twitter:image")
                or _first_image(soup)
            ),
            "category": scraper._category_from_html(soup),
            "availability": scraper._availability_from_html(soup),
        }

    return scraper._generic_price_from_html(html)
