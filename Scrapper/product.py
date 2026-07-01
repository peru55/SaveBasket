"""Shared product validation and normalization helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SOURCE_BY_DOMAIN = {
    "naivas.online": "Naivas",
    "quickmart.co.ke": "Quickmart",
    "carrefour.ke": "Carrefour",
    "cleanshelf.online": "CleanShelf",
    "api.cleanshelf.online": "CleanShelf",
}


@dataclass(frozen=True)
class ProductRecord:
    name: str | None
    price: float | None
    image_url: str | None
    category: str | None
    availability: str
    source: str
    currency: str = "KES"
    url: str | None = None
    sku: str | None = None
    barcode: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "title": self.name,
            "price": self.price,
            "currency": self.currency,
            "image_url": self.image_url,
            "category": self.category,
            "availability": self.availability,
            "source": self.source,
        }
        if self.url:
            data["url"] = self.url
        if self.sku:
            data["sku"] = self.sku
        if self.barcode:
            data["barcode"] = self.barcode
        if self.error:
            data["error"] = self.error
        return data


def source_from_domain(domain: str) -> str:
    for key, source in SOURCE_BY_DOMAIN.items():
        if key in domain:
            return source
    return domain or "Unknown"


def normalize_product_name(name: str | None) -> str | None:
    """Normalize names for cross-supermarket matching."""
    if not name:
        return None
    normalized = name.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None


def validate_product(raw: dict[str, Any] | None, *, source: str, url: str | None = None) -> dict[str, Any]:
    """Return a stable product dict while preserving parser compatibility."""
    raw = raw or {}
    name = raw.get("name") or raw.get("title")
    price = raw.get("price")
    if price is not None:
        try:
            price = float(price)
            if price < 0:
                price = None
        except (TypeError, ValueError):
            price = None

    availability = str(raw.get("availability") or "unknown").strip().lower()
    if availability not in {"in_stock", "out_of_stock", "unknown"}:
        availability = "unknown"

    product = ProductRecord(
        name=str(name).strip() if name else None,
        price=price,
        image_url=raw.get("image_url") or raw.get("image"),
        category=raw.get("category"),
        availability=availability,
        source=raw.get("source") or source,
        currency=raw.get("currency") or "KES",
        url=raw.get("url") or url,
        sku=raw.get("sku"),
        barcode=raw.get("barcode"),
        error=raw.get("error"),
    ).to_dict()
    product["normalized_name"] = normalize_product_name(product["name"])
    return product


def stable_product_key(product: dict[str, Any]) -> str | None:
    """Return a stable product identity for duplicate detection."""
    url = product.get("url")
    if url:
        return f"url:{url.strip()}"

    sku = product.get("sku")
    if sku:
        return f"sku:{str(sku).strip().lower()}"

    barcode = product.get("barcode")
    if barcode:
        return f"barcode:{str(barcode).strip()}"

    normalized_name = product.get("normalized_name") or normalize_product_name(product.get("name"))
    if normalized_name:
        return f"name:{normalized_name}"

    return None
