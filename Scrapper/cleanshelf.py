"""CleanShelf-specific parser for SaveBasket."""

import logging
import math
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from product import validate_product

logger = logging.getLogger("ethical_scraper.cleanshelf")

CLEANSHELF_BASE_URL = "https://cleanshelf.online"
CLEANSHELF_API_BASE = f"{CLEANSHELF_BASE_URL}/api/v1"


def parse_cleanshelf(scraper, url: str, html: str) -> dict:
    """Parse a CleanShelf product page.

    CleanShelf is a Next.js storefront backed by JSON endpoints. Product detail
    pages expose the slug in /product/{slug}, and the matching API endpoint is
    /api/v1/storefront/products/{slug}. HTML parsing is kept as a fallback.
    """
    slug = _product_slug(url)
    if slug:
        api_result = cleanshelf_product_from_api(scraper, slug, referer=url)
        if api_result.get("price") is not None or api_result.get("title"):
            return api_result

    return cleanshelf_product_from_html(scraper, url, html)


def cleanshelf_product_from_api(scraper, slug: str, referer: str | None = None) -> dict:
    """Fetch one CleanShelf product by slug from the storefront API."""
    api_url = f"{CLEANSHELF_API_BASE}/storefront/products/{quote(slug)}"
    try:
        payload = scraper.fetch_json(
            api_url,
            headers=_api_headers(referer or f"{CLEANSHELF_BASE_URL}/product/{slug}"),
        )
    except Exception as exc:
        logger.warning("CleanShelf product API failed for %s: %s", slug, exc)
        return {"title": None, "price": None, "currency": None}

    product = (payload.get("data") or {}).get("product")
    if not isinstance(product, dict):
        return {"title": None, "price": None, "currency": None}
    return product_from_api_item(product)


def fetch_cleanshelf_categories(scraper) -> list[dict]:
    """Fetch CleanShelf category metadata from the storefront API."""
    payload = scraper.fetch_json(
        f"{CLEANSHELF_API_BASE}/storefront/categories",
        headers=_api_headers(f"{CLEANSHELF_BASE_URL}/shop"),
    )
    categories = (payload.get("data") or {}).get("categories") or []
    return [category for category in categories if isinstance(category, dict)]


def fetch_cleanshelf_products(
    scraper,
    *,
    category_slug: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 100,
) -> tuple[list[dict], dict]:
    """Fetch one paginated CleanShelf product API page."""
    params = {"page": str(max(1, page)), "limit": str(max(1, limit))}
    if category_slug:
        params["category_slug"] = category_slug
    if search:
        params["search"] = search

    query = "&".join(f"{key}={quote(value)}" for key, value in params.items())
    payload = scraper.fetch_json(
        f"{CLEANSHELF_API_BASE}/storefront/products?{query}",
        headers=_api_headers(f"{CLEANSHELF_BASE_URL}/shop"),
    )
    data = payload.get("data") or {}
    raw_products = data.get("products") or []
    products = [
        validate_product(product_from_api_item(item), source="CleanShelf")
        for item in raw_products
        if isinstance(item, dict)
    ]
    meta = {
        "total": data.get("total"),
        "page": data.get("page", page),
        "limit": data.get("limit", limit),
    }
    return products, meta


def fetch_cleanshelf_category_products(
    scraper,
    category_slug: str,
    *,
    limit: int = 100,
    max_pages: int | None = None,
) -> list[dict]:
    """Traverse a CleanShelf category with duplicate-safe pagination."""
    products: list[dict] = []
    seen_urls: set[str] = set()
    page = 1
    total_pages = None

    while True:
        page_products, meta = fetch_cleanshelf_products(
            scraper,
            category_slug=category_slug,
            page=page,
            limit=limit,
        )
        new_count = 0
        for product in page_products:
            key = product.get("url") or product.get("normalized_name") or product.get("name")
            if not key or key in seen_urls:
                continue
            seen_urls.add(key)
            products.append(product)
            new_count += 1

        total = _int_or_none(meta.get("total"))
        page_limit = _int_or_none(meta.get("limit")) or limit
        if total is not None and page_limit:
            total_pages = max(1, math.ceil(total / page_limit))

        if new_count == 0:
            break
        if total_pages is not None and page >= total_pages:
            break
        if max_pages is not None and page >= max_pages:
            break
        page += 1

    return products


def product_from_api_item(item: dict) -> dict:
    """Map a CleanShelf API product object to the scraper product contract."""
    slug = item.get("slug")
    category = item.get("category") or {}
    price = item.get("sale_price") or item.get("price")
    category_name = category.get("name") if isinstance(category, dict) else None
    return {
        "title": _title_case(item.get("name")),
        "price": price,
        "currency": "KES",
        "image_url": _image_from_api_item(item),
        "category": _title_case(category_name),
        "availability": _availability_from_api_item(item),
        "source": "CleanShelf",
        "url": urljoin(CLEANSHELF_BASE_URL, f"/product/{slug}") if slug else None,
    }


def cleanshelf_product_from_html(scraper, url: str, html: str) -> dict:
    """Fallback parser for CleanShelf server-rendered product pages."""
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one("h1[class*=title], h1")
    title = title_el.get_text(" ", strip=True) if title_el else None
    detail = title_el.parent if title_el else soup
    price = None
    if detail:
        price = scraper._parse_money(detail.get_text(" ", strip=True))
    if price is None:
        price = scraper._generic_price_from_html(html).get("price")

    image_url = None
    image_scope = title_el
    for _ in range(3):
        image_scope = image_scope.parent if image_scope else None
    if image_scope:
        image = image_scope.find("img")
        if image:
            image_url = _clean_image_url(image.get("src"))

    category = _category_from_breadcrumb(soup, title)
    return {
        "title": title,
        "price": price,
        "currency": "KES" if price is not None else None,
        "image_url": image_url,
        "category": category,
        "availability": scraper._availability_from_html(soup),
        "source": "CleanShelf",
        "url": url,
    }


def _api_headers(referer: str) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
        "Referer": referer,
        "Origin": CLEANSHELF_BASE_URL,
    }


def _product_slug(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    if not path.startswith("product/"):
        return None
    slug = path.split("/", 1)[1].strip("/")
    return unquote(slug) if slug else None


def _image_from_api_item(item: dict) -> str | None:
    images = item.get("images") or []
    if isinstance(images, list) and images:
        ordered = sorted(
            [image for image in images if isinstance(image, dict)],
            key=lambda image: image.get("order") or 0,
        )
        if ordered:
            return _clean_image_url(ordered[0].get("url"))
    image = item.get("image")
    if isinstance(image, str):
        return _clean_image_url(image)
    return None


def _clean_image_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("/_next/image"):
        query = parse_qs(urlparse(url).query)
        source = query.get("url", [None])[0]
        return source if source else urljoin(CLEANSHELF_BASE_URL, url)
    return urljoin(CLEANSHELF_BASE_URL, url)


def _availability_from_api_item(item: dict) -> str:
    branch_stock = item.get("branchStock") or []
    if isinstance(branch_stock, list) and branch_stock:
        if any(bool(branch.get("is_in_stock")) for branch in branch_stock if isinstance(branch, dict)):
            return "in_stock"
        return "out_of_stock"

    stock_status = str(item.get("stock_status") or "").lower()
    if stock_status in {"instock", "in_stock"}:
        return "in_stock"
    if stock_status in {"outofstock", "out_of_stock"}:
        return "out_of_stock"
    return "unknown"


def _category_from_breadcrumb(soup: BeautifulSoup, title: str | None) -> str | None:
    crumbs = [
        crumb.get_text(" ", strip=True)
        for crumb in soup.select("[class*=breadcrumb] a, [class*=breadcrumb] span")
        if crumb.get_text(strip=True)
    ]
    if crumbs:
        ignored = {"home", "shop"}
        candidates = [crumb for crumb in crumbs if crumb.lower() not in ignored and crumb != title]
        if candidates:
            return candidates[-1]
    return None


def _title_case(value: str | None) -> str | None:
    if not value:
        return None
    if value.isupper():
        return value.title()
    return value


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
