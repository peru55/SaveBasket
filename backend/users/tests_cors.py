from django.test import TestCase


class RegistrationCorsTests(TestCase):
    def preflight(self, origin):
        return self.client.options(
            "/api/auth/register/",
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )

    def test_allows_localhost_with_random_flutter_port(self):
        response = self.preflight("http://localhost:52498")

        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "http://localhost:52498",
        )

    def test_rejects_unrelated_origin(self):
        response = self.preflight("https://evil.example")

        self.assertNotIn("Access-Control-Allow-Origin", response)
