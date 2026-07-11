from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Product

from .models import Basket, BasketItem


class BasketOwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="basket-owner",
            password="S4veBasket-Test-Only!2026",
        )
        self.other_user = User.objects.create_user(
            username="basket-other",
            password="S4veBasket-Test-Only!2026",
        )
        self.owner_basket = Basket.objects.create(user=self.owner, name="Owner Basket")
        self.other_basket = Basket.objects.create(user=self.other_user, name="Other Basket")
        self.product = Product.objects.create(name="Ownership Product")
        BasketItem.objects.create(
            basket=self.owner_basket,
            product=self.product,
            quantity=1,
        )
        self.client = APIClient()

    def test_list_contains_only_current_users_baskets(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/baskets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data},
            {str(self.owner_basket.id)},
        )

    def test_non_owner_cannot_retrieve_basket(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.get(f"/api/baskets/{self.owner_basket.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_use_basket_actions(self):
        self.client.force_authenticate(self.other_user)
        basket_url = f"/api/baskets/{self.owner_basket.id}"
        requests = (
            ("post", f"{basket_url}/add_item/", {"product_id": str(self.product.id), "quantity": 1}),
            ("post", f"{basket_url}/remove_item/", {"product_id": str(self.product.id)}),
            ("post", f"{basket_url}/update_item_quantity/", {"product_id": str(self.product.id), "quantity": 2}),
            ("get", f"{basket_url}/compare/", None),
            ("put", f"{basket_url}/", {"name": "Taken Over"}),
            ("delete", f"{basket_url}/", None),
        )

        for method, url, payload in requests:
            with self.subTest(method=method, url=url):
                request = getattr(self.client, method)
                if payload is None:
                    response = request(url)
                else:
                    response = request(url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
