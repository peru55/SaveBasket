"""Tests for JSON product persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from json_store import persist_product, product_file_path


class JsonStoreTests(unittest.TestCase):
    def setUp(self):
        self.product = {
            "name": "Brookside Fresh Milk 1L",
            "title": "Brookside Fresh Milk 1L",
            "price": 135.0,
            "currency": "KES",
            "image_url": "https://example.com/image.jpg",
            "category": "Dairy",
            "availability": "in_stock",
            "source": "Naivas",
            "url": "https://www.naivas.online/brookside-fresh-milk-1l",
            "sku": "18004013",
            "barcode": None,
            "normalized_name": "brookside fresh milk 1l",
        }

    def test_product_file_path_is_stable(self):
        path = product_file_path(self.product, root_dir=Path("/tmp/store"))
        self.assertEqual(path.parent.name, "naivas")
        self.assertIn("naivas__naivas.online__sku__18004013", path.name)

    def test_create_skip_and_update_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            created = persist_product(self.product, root_dir=root)
            self.assertEqual(created.status, "created")
            self.assertTrue(created.path.exists())

            with created.path.open("r", encoding="utf-8") as fh:
                created_payload = json.load(fh)
            self.assertEqual(created_payload["current"]["price"], 135.0)
            self.assertEqual(len(created_payload["history"]), 1)

            skipped = persist_product(self.product, root_dir=root)
            self.assertEqual(skipped.status, "skipped")

            changed_product = dict(self.product)
            changed_product["price"] = 140.0
            updated = persist_product(changed_product, root_dir=root)
            self.assertEqual(updated.status, "updated")

            with updated.path.open("r", encoding="utf-8") as fh:
                updated_payload = json.load(fh)
            self.assertEqual(updated_payload["current"]["price"], 140.0)
            self.assertEqual(len(updated_payload["history"]), 2)
            self.assertEqual(updated_payload["history"][-1]["previous_price"], 135.0)