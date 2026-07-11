"""Manual registration checks against a running SaveBasket backend.

This script intentionally lives outside Django's ``test_*.py`` discovery path.
It never runs during the automated test suite.
"""

import json
import os

import requests


BACKEND_URL = os.getenv("SAVEBASKET_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
REGISTER_URL = f"{BACKEND_URL}/api/auth/register/"

TEST_CASES = (
    ({"username": "", "email": "", "password": ""}, "Empty fields"),
    ({"username": "manual_bad_email", "email": "bad", "password": "S4veBasket-Test-Only!2026"}, "Bad email format"),
    ({"username": "manual_short", "email": "short@example.com", "password": "123"}, "Short password"),
    ({}, "Missing all fields"),
)


def main():
    for payload, description in TEST_CASES:
        response = requests.post(REGISTER_URL, json=payload, timeout=10)
        print(f"\n--- {description} ---")
        print(f"Status: {response.status_code}")
        try:
            print(f"Body: {json.dumps(response.json(), indent=2)}")
        except ValueError:
            print(f"Body: {response.text}")


if __name__ == "__main__":
    main()
