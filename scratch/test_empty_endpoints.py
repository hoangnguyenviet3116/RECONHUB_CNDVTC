import requests

endpoints = [
    ("GET", "http://127.0.0.1:8000/shifts"),
    ("GET", "http://127.0.0.1:8000/orders"),
    ("GET", "http://127.0.0.1:8000/bank-transactions"),
    ("GET", "http://127.0.0.1:8000/payment-allocations"),
    ("GET", "http://127.0.0.1:8000/dashboard/summary"),
    ("GET", "http://127.0.0.1:8000/dashboard/verify-chain")
]

for method, url in endpoints:
    try:
        r = requests.request(method, url)
        print(f"{method} {url} -> Status {r.status_code}")
        if r.status_code >= 400:
            print(f"   Payload: {r.text}")
        else:
            data = r.json()
            if isinstance(data, list):
                print(f"   Items: {len(data)}")
            elif isinstance(data, dict):
                print(f"   Keys: {list(data.keys())[:6]}")
    except Exception as e:
        print(f"{method} {url} -> Error: {e}")
