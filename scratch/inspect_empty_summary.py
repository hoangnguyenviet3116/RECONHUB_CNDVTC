import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests, json

r1 = requests.get("http://127.0.0.1:8000/dashboard/summary").json()
print("=== DASHBOARD SUMMARY ===")
print("shift_name:", r1.get("shift_name"))
print("valid_order_total:", r1.get("valid_order_total"))
print("total_bank_received:", r1.get("total_bank_received"))
print("allocated_payment_total:", r1.get("allocated_payment_total"))
print("ledger_integrity_valid:", r1.get("ledger_integrity_valid"))
print("orders count:", len(r1.get("orders", [])))
print("available_shifts count:", len(r1.get("available_shifts", [])))

r2 = requests.get("http://127.0.0.1:8000/dashboard/verify-chain").json()
print("\n=== VERIFY CHAIN ===")
print("status:", r2.get("status"))
print("is_valid:", r2.get("is_valid"))
print("message:", r2.get("message"))
print("total_records:", r2.get("total_records"))
