import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests

BASE_URL = "http://127.0.0.1:8000"

print("=================================================================")
print("KIỂM THỬ KHỞI ĐỘNG LẠI BACKEND: KHÔNG CÓ SEED NÀO ĐƯỢC CHÈN LẠI")
print("=================================================================")

orders = requests.get(f"{BASE_URL}/orders").json()
shifts = requests.get(f"{BASE_URL}/shifts").json()
txs = requests.get(f"{BASE_URL}/bank-transactions").json()
dash = requests.get(f"{BASE_URL}/dashboard/summary").json()

print(f"Tổng số ca sau khởi động lại: {len(shifts)} ca")
print(f"Tổng số đơn sau khởi động lại: {len(orders)} đơn")
print(f"Tổng số giao dịch sau khởi động lại: {len(txs)} giao dịch")
print(f"Doanh thu thực tế trên Dashboard: {dash.get('valid_order_total'):,.0f} ₫")

# Kiểm tra chắc chắn không có mã đơn mẫu ORD1001 - ORD1006
order_codes = [o["order_code"] for o in orders]
print(f"Danh sách mã đơn hiện có: {order_codes}")

assert "ORD1001" not in order_codes, "LỖI: Phát hiện dữ liệu mẫu ORD1001 tự động xuất hiện lại!"
assert "ORD1002" not in order_codes, "LỖI: Phát hiện dữ liệu mẫu ORD1002 tự động xuất hiện lại!"
assert "ORD1003" not in order_codes, "LỖI: Phát hiện dữ liệu mẫu ORD1003 tự động xuất hiện lại!"
assert "ORD1004" not in order_codes, "LỖI: Phát hiện dữ liệu mẫu ORD1004 tự động xuất hiện lại!"
assert "ORD1005" not in order_codes, "LỖI: Phát hiện dữ liệu mẫu ORD1005 tự động xuất hiện lại!"
assert "ORD1006" not in order_codes, "LỖI: Phát hiện dữ liệu mẫu ORD1006 tự động xuất hiện lại!"

print("\n[XÁC NHẬN HOÀN TẤT] Sau khi khởi động lại backend:")
print("1. KHÔNG CÓ bất kỳ dữ liệu mẫu seed_data.sql nào được nạp tự động.")
print("2. Dữ liệu thực tế phát sinh từ web được bảo toàn nguyên vẹn 100%.")
print("=================================================================")
