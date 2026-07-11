from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from supermarkets.models import Branch, Supermarket

from .models import IngestionHistory, RawScrapedProduct


class ScraperIngestSecurityTests(TestCase):
    payload = {
        "source": "Security Test Market",
        "products": [
            {
                "name": "Security Test Milk 1L",
                "price": "100.00",
                "url": "https://example.com/security-test-milk",
            }
        ],
    }

    def setUp(self):
        self.client = APIClient()

    def assert_no_ingestion_rows(self):
        self.assertEqual(IngestionHistory.objects.count(), 0)
        self.assertEqual(RawScrapedProduct.objects.count(), 0)
        self.assertEqual(Supermarket.objects.count(), 0)
        self.assertEqual(Branch.objects.count(), 0)

    @override_settings(DEBUG=False, SCRAPER_API_KEY=None)
    def test_production_rejects_ingest_when_key_is_not_configured(self):
        response = self.client.post("/api/scraper/ingest/", self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_ingestion_rows()

    @override_settings(DEBUG=False, SCRAPER_API_KEY="expected-key")
    def test_production_rejects_invalid_key_before_creating_rows(self):
        response = self.client.post(
            "/api/scraper/ingest/",
            self.payload,
            format="json",
            HTTP_X_SCRAPER_KEY="wrong-key",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_ingestion_rows()

    @override_settings(DEBUG=False, SCRAPER_API_KEY="expected-key")
    def test_production_accepts_valid_key(self):
        response = self.client.post(
            "/api/scraper/ingest/",
            self.payload,
            format="json",
            HTTP_X_SCRAPER_KEY="expected-key",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(IngestionHistory.objects.count(), 1)
        self.assertEqual(RawScrapedProduct.objects.count(), 1)
