"""Product matching and creation helpers used by the ingestion pipeline.

This module centralizes product-identification logic so the ingestion view
can remain small and tests can exercise matching behaviors.
"""
from __future__ import annotations

from typing import Optional, Tuple, Dict, Any
from django.db import IntegrityError, transaction

from .models import Product
from .utils import normalize_name


def find_product_by_identifiers(barcode: Optional[str], sku: Optional[str]) -> Optional[Product]:
    if barcode:
        p = Product.objects.filter(barcode=barcode).first()
        if p:
            return p
    if sku:
        p = Product.objects.filter(sku=sku).first()
        if p:
            return p
    return None


def find_product_by_normalized_name(name: Optional[str]) -> Optional[Product]:
    if not name:
        return None
    norm = normalize_name(name)
    if not norm:
        return None
    return Product.objects.filter(normalized_name=norm).first()


def get_or_create_product(raw: Dict[str, Any]) -> Tuple[Product, bool]:
    """Find an existing Product or create a new one.

    Matching order:
      1. barcode
      2. sku
      3. normalized_name

    Returns (product, created_boolean).
    """
    name = (raw.get("name") or raw.get("title") or "").strip()
    sku = raw.get("sku")
    barcode = raw.get("barcode")

    # Fast identifier-based lookup
    product = find_product_by_identifiers(barcode, sku)
    if product:
        return product, False

    # Try normalized name lookup (uses indexed column)
    if name:
        product = find_product_by_normalized_name(name)
        if product:
            return product, False

    # Create a new product; gracefully handle unique constraint races
    try:
        with transaction.atomic():
            p = Product.objects.create(
                name=name or "",
                sku=sku or None,
                barcode=barcode or None,
                category=raw.get("category"),
                brand=raw.get("brand"),
                image_url=raw.get("image_url") or raw.get("image"),
                description=raw.get("description") or "",
            )
            return p, True
    except IntegrityError:
        # Race: another process created a product with the same sku/barcode
        fallback = find_product_by_identifiers(barcode, sku) or find_product_by_normalized_name(name)
        if fallback:
            return fallback, False
        # As a last resort return any product matching the exact name
        p = Product.objects.filter(name=name).first()
        if p:
            return p, False
        # If we still don't have one, re-raise
        raise
