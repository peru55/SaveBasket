"""Generic JSON persistence for scraped products.

The store keeps one file per product identity so unchanged products are not
rewritten. Each product file stores the current snapshot plus a change history.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = 1
DEFAULT_STORE_ROOT = Path(__file__).resolve().parent / "data"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def sanitize_fragment(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    fragment = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-_.")
    return fragment or fallback


def _identity_candidates(product: dict[str, Any]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for field in ("barcode", "sku", "normalized_name"):
        value = product.get(field)
        if value:
            candidates.append((field, sanitize_fragment(str(value).strip().lower())))

    url = product.get("url")
    if url:
        parsed = urlparse(str(url))
        path = parsed.path.strip("/") or parsed.netloc
        candidates.append(("url", sanitize_fragment(path.lower())))

    return candidates


def build_product_key(product: dict[str, Any]) -> dict[str, str]:
    """Build a stable identity for a scraped product.

    Priority order:
    1. barcode
    2. sku
    3. normalized_name
    4. url path
    5. content hash fallback
    """

    source = str(product.get("source") or "Unknown")
    source_slug = slugify(source)
    source_domain = str(urlparse(str(product.get("url") or "")).netloc or "").lower()
    source_domain = source_domain[4:] if source_domain.startswith("www.") else source_domain

    candidates = _identity_candidates(product)
    if candidates:
        key_type, key_value = candidates[0]
    else:
        digest_source = json.dumps(product, sort_keys=True, ensure_ascii=False).encode("utf-8")
        key_type = "hash"
        key_value = hashlib.sha1(digest_source).hexdigest()[:16]

    product_key = f"{source_slug}__{key_type}__{key_value}"
    if source_domain:
        product_key = f"{source_slug}__{source_domain}__{key_type}__{key_value}"

    return {
        "source_slug": source_slug,
        "source_domain": source_domain,
        "key_type": key_type,
        "key_value": key_value,
        "product_key": product_key,
    }


def product_file_path(product: dict[str, Any], root_dir: str | Path | None = None) -> Path:
    root = Path(root_dir) if root_dir else DEFAULT_STORE_ROOT
    identity = build_product_key(product)
    source_dir = root / identity["source_slug"]
    return source_dir / f"{identity['product_key']}.json"


def load_product_record(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _history_event(event_type: str, product: dict[str, Any], *, previous_price: float | None = None) -> dict[str, Any]:
    event = {
        "event_type": event_type,
        "seen_at": utc_now_iso(),
        "price": product.get("price"),
        "currency": product.get("currency") or "KES",
        "name": product.get("name") or product.get("title"),
        "url": product.get("url"),
    }
    if previous_price is not None:
        event["previous_price"] = previous_price
    return event


def _current_snapshot(product: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    now = utc_now_iso()
    snapshot = {
        "name": product.get("name") or product.get("title"),
        "title": product.get("title") or product.get("name"),
        "price": product.get("price"),
        "currency": product.get("currency") or "KES",
        "image_url": product.get("image_url"),
        "category": product.get("category"),
        "availability": product.get("availability") or "unknown",
        "source": product.get("source") or "Unknown",
        "url": product.get("url"),
        "sku": product.get("sku"),
        "barcode": product.get("barcode"),
        "normalized_name": product.get("normalized_name"),
        "identity": build_product_key(product),
        "last_seen_at": now,
    }

    if existing and isinstance(existing.get("current"), dict):
        current = existing["current"]
        snapshot["first_seen_at"] = current.get("first_seen_at") or now
        snapshot["price_history"] = list(current.get("price_history") or [])
        snapshot["aliases"] = dict(current.get("aliases") or {})
    else:
        snapshot["first_seen_at"] = now
        snapshot["price_history"] = []
        snapshot["aliases"] = {"urls": [], "skus": [], "barcodes": []}

    aliases = snapshot["aliases"]
    for field, alias_key in (("url", "urls"), ("sku", "skus"), ("barcode", "barcodes")):
        value = product.get(field)
        if value:
            current_values = aliases.setdefault(alias_key, [])
            if value not in current_values:
                current_values.append(value)

    return snapshot


@dataclass
class PersistResult:
    status: str
    path: Path
    product_key: str
    key_type: str
    changed: bool
    previous_price: float | None = None
    current_price: float | None = None


def persist_product(product: dict[str, Any], root_dir: str | Path | None = None) -> PersistResult:
    """Persist a single product snapshot if it is new or its price changed.

    Returns a PersistResult with status one of:
    - "created" for a new product file
    - "updated" for an existing product whose price changed
    - "skipped" for unchanged products
    """

    path = product_file_path(product, root_dir=root_dir)
    existing = load_product_record(path)
    current_price = product.get("price")

    if existing is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = _current_snapshot(product)
        snapshot["price_history"] = [
            {
                "event_type": "new",
                "seen_at": snapshot["first_seen_at"],
                "price": current_price,
                "currency": snapshot["currency"],
            }
        ]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "product_key": snapshot["identity"]["product_key"],
            "source": snapshot["source"],
            "source_domain": snapshot["identity"].get("source_domain") or None,
            "created_at": snapshot["first_seen_at"],
            "updated_at": snapshot["last_seen_at"],
            "current": snapshot,
            "history": [_history_event("new", product)],
        }
        _atomic_write_json(path, payload)
        return PersistResult(
            status="created",
            path=path,
            product_key=snapshot["identity"]["product_key"],
            key_type=snapshot["identity"]["key_type"],
            changed=True,
            current_price=current_price,
        )

    existing_current = existing.get("current") or {}
    existing_price = existing_current.get("price")
    if existing_price == current_price:
        return PersistResult(
            status="skipped",
            path=path,
            product_key=str(existing.get("product_key") or build_product_key(product)["product_key"]),
            key_type=str(existing_current.get("identity", {}).get("key_type") or build_product_key(product)["key_type"]),
            changed=False,
            previous_price=existing_price,
            current_price=current_price,
        )

    snapshot = _current_snapshot(product, existing=existing)
    previous_price = existing_price
    snapshot["price_history"] = list(snapshot.get("price_history") or []) + [
        {
            "event_type": "price_change",
            "seen_at": snapshot["last_seen_at"],
            "price": current_price,
            "previous_price": previous_price,
            "currency": snapshot["currency"],
        }
    ]
    payload = {
        "schema_version": existing.get("schema_version") or SCHEMA_VERSION,
        "product_key": existing.get("product_key") or snapshot["identity"]["product_key"],
        "source": existing.get("source") or snapshot["source"],
        "source_domain": existing.get("source_domain") or snapshot["identity"].get("source_domain") or None,
        "created_at": existing.get("created_at") or snapshot["first_seen_at"],
        "updated_at": snapshot["last_seen_at"],
        "current": snapshot,
        "history": list(existing.get("history") or []) + [_history_event("price_change", product, previous_price=previous_price)],
    }
    _atomic_write_json(path, payload)
    return PersistResult(
        status="updated",
        path=path,
        product_key=payload["product_key"],
        key_type=snapshot["identity"]["key_type"],
        changed=True,
        previous_price=previous_price,
        current_price=current_price,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    temp_path.replace(path)