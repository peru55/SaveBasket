from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from supermarkets.models import Branch, Supermarket

from .models import Product


class ProductPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="product-user",
            password="S4veBasket-Test-Only!2026",
        )
        self.staff = User.objects.create_user(
            username="product-staff",
            password="S4veBasket-Test-Only!2026",
            is_staff=True,
        )
        supermarket = Supermarket.objects.create(name="Permission Market")
        self.branch = Branch.objects.create(supermarket=supermarket, name="Website")
        self.product = Product.objects.create(name="Existing Product")

    def test_anonymous_users_can_read_products_and_prices(self):
        self.assertEqual(self.client.get("/api/products/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/prices/").status_code, status.HTTP_200_OK)

    def test_normal_users_cannot_create_products_or_prices(self):
        self.client.force_authenticate(self.user)

        product_response = self.client.post(
            "/api/products/",
            {"name": "User Product"},
            format="json",
        )
        price_response = self.client.post(
            "/api/prices/",
            {
                "product_id": str(self.product.id),
                "branch_id": str(self.branch.id),
                "price": "99.00",
            },
            format="json",
        )

        self.assertEqual(product_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(price_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_users_can_create_products_and_prices(self):
        self.client.force_authenticate(self.staff)

        product_response = self.client.post(
            "/api/products/",
            {"name": "Staff Product"},
            format="json",
        )
        price_response = self.client.post(
            "/api/prices/",
            {
                "product_id": str(self.product.id),
                "branch_id": str(self.branch.id),
                "price": str(Decimal("99.00")),
            },
            format="json",
        )

        self.assertEqual(product_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(price_response.status_code, status.HTTP_201_CREATED)
