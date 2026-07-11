from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from savebasket.config import split_env_list, validate_production_settings


class ProductionConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.valid_values = {
            "SECRET_KEY": "test-only-secret",
            "ALLOWED_HOSTS": ["api.example.com"],
            "SCRAPER_API_KEY": "test-only-scraper-key",
            "CORS_ALLOWED_ORIGINS": ["https://app.example.com"],
        }

    def test_split_env_list_trims_and_removes_empty_items(self):
        self.assertEqual(
            split_env_list(" api.example.com, ,localhost "),
            ["api.example.com", "localhost"],
        )

    def test_development_allows_missing_production_values(self):
        validate_production_settings(True, {})

    def test_production_rejects_each_missing_required_value(self):
        for key in self.valid_values:
            with self.subTest(key=key):
                values = dict(self.valid_values)
                values[key] = [] if isinstance(values[key], list) else ""
                with self.assertRaisesMessage(ImproperlyConfigured, key):
                    validate_production_settings(False, values)

    def test_configuration_error_does_not_include_secret_values(self):
        exposed_value = "never-print-this-secret"
        values = dict(self.valid_values)
        values["SECRET_KEY"] = ""

        with self.assertRaises(ImproperlyConfigured) as caught:
            validate_production_settings(False, values)

        self.assertNotIn(exposed_value, str(caught.exception))
