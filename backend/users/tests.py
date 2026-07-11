from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.token_url = '/api/auth/token/'
        self.refresh_url = '/api/auth/token/refresh/'
        self.baskets_url = '/api/baskets/'

    def test_register_creates_user(self):
        data = {'username': 'tester', 'email': 't@example.com', 'password': 'S4veBasket-Test-Only!2026'}
        resp = self.client.post(self.register_url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username='tester').exists())

    def test_token_obtain_and_refresh(self):
        # create user
        User.objects.create_user(username='apiuser', password='pass1234')
        token_resp = self.client.post(self.token_url, {'username': 'apiuser', 'password': 'pass1234'}, format='json')
        self.assertEqual(token_resp.status_code, 200)
        self.assertIn('access', token_resp.data)
        self.assertIn('refresh', token_resp.data)

        refresh_token = token_resp.data['refresh']
        refresh_resp = self.client.post(self.refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(refresh_resp.status_code, 200)
        self.assertIn('access', refresh_resp.data)

    def test_protected_endpoint_requires_auth(self):
        # no auth -> 401
        resp = self.client.get(self.baskets_url)
        self.assertIn(resp.status_code, (401, 403))

        # create user and obtain token
        User.objects.create_user(username='apibuyer', password='buy1234')
        token_resp = self.client.post(self.token_url, {'username': 'apibuyer', 'password': 'buy1234'}, format='json')
        access = token_resp.data.get('access')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp2 = self.client.get(self.baskets_url)
        # should be allowed (empty list or 200)
        self.assertIn(resp2.status_code, (200, 204))
