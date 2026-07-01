from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

from .models import Product, StoreProduct
from .serializers import ProductSerializer


class ProductSearchSerializationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Pembe Flour",
            normalized_name="pembe flour",
            brand="pembe",
        )
        StoreProduct.objects.create(
            product=self.product,
            store_name="Carrefour",
            store_product_name="Pembe Flour",
            price=Decimal("160.00"),
        )
        StoreProduct.objects.create(
            product=self.product,
            store_name="Naivas",
            store_product_name="Pembe Flour",
            price=Decimal("150.00"),
        )
        StoreProduct.objects.create(
            product=self.product,
            store_name="Quickmart",
            store_product_name="Pembe Flour",
            price=Decimal("155.00"),
        )

    def test_serializer_returns_all_store_products_for_canonical_product(self):
        data = ProductSerializer(self.product).data

        self.assertEqual(len(data["stores"]), 3)
        self.assertEqual(
            {store["store"] for store in data["stores"]},
            {"Carrefour", "Naivas", "Quickmart"},
        )

    def test_search_returns_single_canonical_product_with_all_stores(self):
        response = APIClient().get("/api/products/", {"search": "Pembe Flour"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.product.id))
        self.assertEqual(
            {store["store"] for store in response.data[0]["stores"]},
            {"Carrefour", "Naivas", "Quickmart"},
        )

    def test_search_returns_proxied_product_image_url(self):
        self.product.image_url = "https://cfn.quickmart.co.ke/example.png"
        self.product.save()

        response = APIClient().get("/api/products/", {"search": "Pembe Flour"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/products/image-proxy/?url=", response.data[0]["image_url"])

    def test_search_falls_back_to_store_product_image_url(self):
        self.product.image_url = None
        self.product.save()
        store_product = self.product.store_products.get(store_name="Quickmart")
        store_product.scraped_image_url = "https://cfn.quickmart.co.ke/store-product.png"
        store_product.save()

        response = APIClient().get("/api/products/", {"search": "Pembe Flour"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/products/image-proxy/?url=", response.data[0]["image_url"])

    def test_serializer_prefers_same_store_image_before_other_store_fallback(self):
        self.product.image_url = None
        self.product.save()
        naivas = self.product.store_products.get(store_name="Naivas")
        quickmart = self.product.store_products.get(store_name="Quickmart")
        naivas.scraped_image_url = "https://naivas.online/pembe.png"
        quickmart.scraped_image_url = "https://cfn.quickmart.co.ke/pembe.png"
        naivas.save()
        quickmart.save()

        data = ProductSerializer(self.product, context={"store_name": "Quickmart"}).data

        self.assertEqual(data["image_url"], "https://cfn.quickmart.co.ke/pembe.png")

    @patch("products.views.requests.get")
    def test_image_proxy_fetches_remote_image_with_browser_headers(self, mock_get):
        remote_response = Mock()
        remote_response.headers = {"Content-Type": "image/png"}
        remote_response.content = b"image-bytes"
        remote_response.raise_for_status.return_value = None
        mock_get.return_value = remote_response

        response = APIClient().get(
            "/api/products/image-proxy/",
            {"url": "https://cfn.quickmart.co.ke/example.png"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, b"image-bytes")
        headers = mock_get.call_args.kwargs["headers"]
        self.assertIn("Mozilla", headers["User-Agent"])
