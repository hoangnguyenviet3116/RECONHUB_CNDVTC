import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import requests

r = requests.get("http://127.0.0.1:8000/shifts")
print("Status:", r.status_code)
print("Data:", r.json())
