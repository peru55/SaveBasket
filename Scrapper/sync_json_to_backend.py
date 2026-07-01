"""Backfill local JSON snapshots into the backend ingestion endpoint.

This script scans Scrapper/data/**/*.json and POSTs each snapshot to the
Django ingest endpoint so previously scraped products appear in ingestion
history as well.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from push_to_backend import push_payload


DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


def iter_snapshot_files(data_dir: Path):
    if not data_dir.exists():
        return []
    return sorted(p for p in data_dir.rglob("*.json") if p.is_file())


def snapshot_to_payload(snapshot: dict) -> dict:
    current = snapshot.get("current") or snapshot
    source = snapshot.get("source") or current.get("source") or "Unknown"
    branch = snapshot.get("branch") or current.get("branch") or {"name": "Website", "city": "Nairobi"}

    # The backend accepts a single normalized product in a list. Sending the
    # current snapshot preserves the latest state while creating history rows.
    product = dict(current)
    product["source"] = source
    return {
        "source": source,
        "branch": branch,
        "products": [product],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Backfill JSON snapshots to backend ingestion history.")
    parser.add_argument("--backend", required=True, help="Backend base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--key", help="Optional X-SCRAPER-KEY header value")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing JSON snapshots")
    parser.add_argument("--dry-run", action="store_true", help="Print planned pushes without POSTing")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    files = iter_snapshot_files(data_dir)
    if not files:
        print(f"No JSON snapshots found in {data_dir}")
        return 0

    pushed = 0
    failed = 0
    for file_path in files:
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                snapshot = json.load(fh)
            if not isinstance(snapshot, dict):
                print(f"Skipping non-object JSON: {file_path}")
                continue
            payload = snapshot_to_payload(snapshot)
        except Exception as exc:
            failed += 1
            print(f"Failed to read {file_path}: {exc}")
            continue

        if args.dry_run:
            print(json.dumps({"file": str(file_path), "payload": payload}, indent=2, ensure_ascii=False))
            continue

        status, data = push_payload(args.backend, args.key, payload)
        if 200 <= status < 300:
            pushed += 1
            print(f"Pushed {file_path.name}: status={status}")
        else:
            failed += 1
            print(f"Failed {file_path.name}: status={status} response={data}")

    print(f"Done. pushed={pushed} failed={failed} total={len(files)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())