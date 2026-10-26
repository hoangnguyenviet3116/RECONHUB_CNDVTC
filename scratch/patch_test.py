with open("scratch/test_stage2_blockchain_merkle_biometrics.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add HEADERS to requests
code = code.replace(
    'BASE_URL = "http://127.0.0.1:8000"',
    'BASE_URL = "http://127.0.0.1:8000"\nHEADERS = {"X-Demo-Role": "OWNER", "X-Merchant-Id": "1", "X-User-Id": "1"}'
)

# Replace requests.get and requests.post
code = code.replace('requests.get(f"{BASE_URL}', 'requests.get(f"{BASE_URL}", headers=HEADERS')
code = code.replace('requests.post(f"{BASE_URL}', 'requests.post(f"{BASE_URL}", headers=HEADERS')

# Fix url template replacement syntax
code = code.replace('requests.get(f"{BASE_URL}", headers=HEADERS', 'requests.get(f"{BASE_URL}')
code = code.replace('requests.post(f"{BASE_URL}", headers=HEADERS', 'requests.post(f"{BASE_URL}')

# Let's do it cleanly by writing the full test script with session or default headers
