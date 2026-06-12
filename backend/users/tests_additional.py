from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient


class AuthEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.token_url = '/api/auth/token/'
        self.refresh_url = '/api/auth/token/refresh/'
        self.prices_url = '/api/prices/'

    def test_register_missing_password(self):
        data = {'username': 'no_pw', 'email': 'a@b.com'}
        resp = self.client.post(self.register_url, data, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username(self):
        User.objects.create_user(username='dup', password='x')
        data = {'username': 'dup', 'email': 'd@d.com', 'password': 'abcd1234'}
        resp = self.client.post(self.register_url, data, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_refresh_with_invalid_token(self):
        resp = self.client.post(self.refresh_url, {'refresh': 'not-a-token'}, format='json')
        self.assertIn(resp.status_code, (401, 400))

    def test_product_price_create_requires_auth(self):
        # unauthenticated create should be rejected
        resp = self.client.post(self.prices_url, {'product': 1, 'branch': 1, 'price': '12.34'}, format='json')
        self.assertIn(resp.status_code, (401, 403))
