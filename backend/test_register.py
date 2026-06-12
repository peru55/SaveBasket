import requests
import json

BASE = "http://127.0.0.1:8000/api/auth/register/"

tests = [
    ({"username": "", "email": "", "password": ""}, "Empty fields"),
    ({"username": "test2", "email": "bad", "password": "123456K"}, "Bad email format"),
    ({"username": "test3", "email": "t@t.com", "password": "123"}, "Short password"),
    ({"username": "test4", "email": "t4@t.com", "password": "password"}, "Common password"),
    ({"username": "test5", "email": "t5@t.com", "password": "12345678"}, "Numeric-only password"),
    ({}, "Missing all fields"),
    ({"username": "peru", "email": "peruemanuel6@gmail.com", "password": "123456K"}, "Duplicate user"),
]

for payload, desc in tests:
    r = requests.post(BASE, json=payload)
    print(f"\n--- {desc} ---")
    print(f"Status: {r.status_code}")
    try:
        print(f"Body: {json.dumps(r.json(), indent=2)}")
    except Exception:
        print(f"Body: {r.text}")
