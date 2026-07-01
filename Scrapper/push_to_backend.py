"""Helper to push scraped product batches to the Django backend ingestion endpoint.

Usage examples:
  # Push a single product parsed from a URL
  python push_to_backend.py --backend http://localhost:8000 --url "https://www.naivas.online/...." --key "$KEY"

  # Push a prepared JSON file (either full payload or list of products)
  python push_to_backend.py --backend http://localhost:8000 --file batch.json --key "$KEY" --source CleanShelf
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

import requests

# Import local scraper when run from the Scrapper/ folder
try:
    from scraper import EthicalScraper
except Exception:
    EthicalScraper = None


DEFAULT_INGEST_PATH = "/api/scraper/ingest/"


def normalize_backend_base_url(base_url: str) -> str:
    """Return the backend root URL regardless of whether the user passed /api."""
    parsed = urlsplit(base_url.rstrip("/"))
    path = parsed.path.rstrip("/")
    if path.endswith("/api"):
        path = path[:-4]
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment)).rstrip("/")


def push_payload(base_url: str, api_key: str | None, payload: Dict[str, Any]):
    url = normalize_backend_base_url(base_url) + DEFAULT_INGEST_PATH
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-SCRAPER-KEY"] = api_key
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data


def build_payload_from_file(path: str, source: str | None = None, branch_name: str | None = None, branch_city: str | None = None):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, dict) and ("products" in data or "source" in data):
        # assume full payload already
        payload = data
        if source:
            payload.setdefault("source", source)
        if branch_name:
            payload.setdefault("branch", {"name": branch_name, "city": branch_city or "Nairobi"})
        return payload

    # If file contains a list of products, wrap into payload
    if isinstance(data, list):
        payload = {
            "source": source or "Unknown",
            "branch": {"name": branch_name or "Website", "city": branch_city or "Nairobi"},
            "products": data,
        }
        return payload

    raise ValueError("Unsupported JSON file format: expected dict or list")


def build_payload_from_url(url: str, branch_name: str | None = None, branch_city: str | None = None, source: str | None = None):
    if EthicalScraper is None:
        raise RuntimeError("EthicalScraper not importable. Run this script from Scrapper/ or ensure the package is on PYTHONPATH.")
    s = EthicalScraper()
    print(f"Fetching and parsing {url}...")
    try:
        product = s.scrape_product(url)
    except Exception as exc:
        raise RuntimeError(f"Failed to scrape {url}: {exc}")
    payload = {
        "source": source or product.get("source") or "Unknown",
        "branch": {"name": branch_name or "Website", "city": branch_city or "Nairobi"},
        "products": [product],
    }
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, help="Base URL of backend, e.g. http://localhost:8000")
    parser.add_argument("--key", help="X-SCRAPER-KEY header value (optional)")
    parser.add_argument("--file", help="Path to JSON file containing products or full payload")
    parser.add_argument("--url", help="Single product page URL to scrape and push")
    parser.add_argument("--source", help="Override source/supermarket name")
    parser.add_argument("--branch-name", help="Branch name to attach (default: Website)")
    parser.add_argument("--branch-city", help="Branch city to attach (default: Nairobi)")
    parser.add_argument("--dry-run", action="store_true", help="Don't POST, just print payload")

    args = parser.parse_args(argv)

    if not args.file and not args.url:
        print("Either --file or --url is required.")
        parser.print_help()
        return 2

    if args.file:
        payload = build_payload_from_file(args.file, source=args.source, branch_name=args.branch_name, branch_city=args.branch_city)
    else:
        payload = build_payload_from_url(args.url, branch_name=args.branch_name, branch_city=args.branch_city, source=args.source)

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    status, data = push_payload(args.backend, args.key, payload)
    print(f"Backend responded: {status}")
    print(json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (dict, list)) else data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
