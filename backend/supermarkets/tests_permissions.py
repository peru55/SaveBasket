from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Supermarket


class SupermarketPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="catalog-user",
            password="S4veBasket-Test-Only!2026",
        )
        self.staff = User.objects.create_user(
            username="catalog-staff",
            password="S4veBasket-Test-Only!2026",
            is_staff=True,
        )
        self.supermarket = Supermarket.objects.create(name="Existing Market")

    def test_anonymous_users_can_read_catalog(self):
        self.assertEqual(self.client.get("/api/supermarkets/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/branches/").status_code, status.HTTP_200_OK)

    def test_anonymous_users_cannot_create_catalog_records(self):
        supermarket_response = self.client.post(
            "/api/supermarkets/",
            {"name": "Anonymous Market"},
            format="json",
        )
        branch_response = self.client.post(
            "/api/branches/",
            {"supermarket_id": str(self.supermarket.id), "name": "Anonymous Branch"},
            format="json",
        )

        self.assertIn(supermarket_response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertIn(branch_response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_normal_users_cannot_create_catalog_records(self):
        self.client.force_authenticate(self.user)

        supermarket_response = self.client.post(
            "/api/supermarkets/",
            {"name": "User Market"},
            format="json",
        )
        branch_response = self.client.post(
            "/api/branches/",
            {"supermarket_id": str(self.supermarket.id), "name": "User Branch"},
            format="json",
        )

        self.assertEqual(supermarket_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(branch_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_users_can_create_catalog_records(self):
        self.client.force_authenticate(self.staff)

        supermarket_response = self.client.post(
            "/api/supermarkets/",
            {"name": "Staff Market"},
            format="json",
        )
        branch_response = self.client.post(
            "/api/branches/",
            {"supermarket_id": str(self.supermarket.id), "name": "Staff Branch"},
            format="json",
        )

        self.assertEqual(supermarket_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(branch_response.status_code, status.HTTP_201_CREATED)
