import os
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")

BASE_URL = "http://127.0.0.1:8000"

def test_production_real_workflow():
    print("=================================================================")
    print("KIỂM THỬ QUY TRÌNH THỰC TẾ TRÊN MÔI TRƯỜNG PRODUCTION (KHÔNG SEED)")
    print("=================================================================")

    # 1. Kiểm tra ban đầu: Database sạch 100% dữ liệu giao dịch mẫu
    orders_init = requests.get(f"{BASE_URL}/orders").json()
    shifts_init = requests.get(f"{BASE_URL}/shifts").json()
    dash_init = requests.get(f"{BASE_URL}/dashboard/summary").json()

    print(f"1. Trạng thái ban đầu: {len(shifts_init)} ca, {len(orders_init)} đơn.")
    assert len(orders_init) == 0, f"LỖI: orders không rỗng ({len(orders_init)} đơn)"
    assert len(shifts_init) == 0, f"LỖI: shifts không rỗng ({len(shifts_init)} ca)"
    assert dash_init.get("valid_order_total") == 0.0, "LỖI: valid_order_total ban đầu không bằng 0"
    print("   -> [PASS] Database sạch hoàn toàn, không có đơn hàng hay ca mẫu nào!")

    # 2. Chủ cửa hàng mở ca bán hàng mới trên Web (index.html)
    now = datetime.now(vn_tz)
    start_time = now.strftime("%Y-%m-%dT%H:%M:%S")
    end_time = (now + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%S")

    shift_payload = {
        "name": "Ca Sáng Bán Lẻ Thực Tế - 24/10/2026",
        "target_revenue": 50000000.0,
        "start_time": start_time,
        "end_time": end_time
    }
    headers_owner = {"X-Demo-Role": "OWNER", "X-Merchant-Id": "1", "X-User-Id": "3"}
    res_shift = requests.post(f"{BASE_URL}/shifts", json=shift_payload, headers=headers_owner)
    assert res_shift.status_code == 201, f"Tạo ca thất bại: {res_shift.text}"
    shift_data = res_shift.json()
    shift_id = shift_data["id"]
    print(f"\n2. Mở ca bán hàng thực tế: Ca #{shift_id} - '{shift_data['name']}' (Status: {shift_data['status']})")
    assert shift_data["status"] == "OPEN"
    print("   -> [PASS] Ca bán hàng thực tế mở thành công!")

    # 3. Thu ngân tạo đơn hàng tại Quầy thu ngân (pos.html)
    order_code = f"ORD_REAL_{int(now.timestamp())}"
    order_payload = {
        "shift_id": shift_id,
        "order_code": order_code,
        "total_amount": 1250000.0,
        "customer_note": "Bàn 02 - Khách dùng bữa trưa"
    }
    headers_cashier = {"X-Demo-Role": "CASHIER", "X-Merchant-Id": "1", "X-User-Id": "1"}
    res_order = requests.post(f"{BASE_URL}/orders", json=order_payload, headers=headers_cashier)
    assert res_order.status_code == 201, f"Tạo đơn thất bại: {res_order.text}"
    order_data = res_order.json()
    order_id = order_data["id"]
    print(f"\n3. Tạo đơn hàng tại POS: #{order_id} - {order_code} (1.250.000 ₫)")
    assert order_data["payment_status"] == "UNPAID"
    print("   -> [PASS] Đơn hàng phát sinh từ Web đã được lưu vào cơ sở dữ liệu!")

    # 4. Thu ngân phát hành mã VietQR cho đơn hàng (Nút Tạo QR)
    qr_payload = {"order_id": order_id, "expected_amount": 1250000.0}
    res_qr = requests.post(f"{BASE_URL}/payment-requests/", json=qr_payload, headers=headers_cashier)
    assert res_qr.status_code == 201, f"Tạo QR thất bại: {res_qr.text}"
    qr_data = res_qr.json()
    print(f"\n4. Phát hành mã VietQR: Request Code '{qr_data['request_code']}'")
    assert qr_data["status"] == "ACTIVE"
    print("   -> [PASS] VietQR động đã sẵn sàng để khách quét thanh toán!")

    # 5. Khách hàng thực hiện chuyển khoản ngân hàng qua Cổng thanh toán (bank-simulator.html)
    tx_time = datetime.now(vn_tz)
    ref_code = f"FTREAL{int(tx_time.timestamp())}"
    bank_payload = {
        "reference_code": ref_code,
        "amount": 1250000.0,
        "transfer_content": f"TT {order_code}",
        "transfer_time": tx_time.isoformat(),
        "transaction_date": tx_time.isoformat()
    }
    res_bank = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json=bank_payload)
    assert res_bank.status_code == 200, f"Chuyển khoản thất bại: {res_bank.text}"
    print(f"\n5. Chuyển khoản ngân hàng thành công: Mã GD '{ref_code}' (1.250.000 ₫)")
    print("   -> [PASS] Webhook tiếp nhận, tự động đối soát và gạch nợ thành công!")

    # 6. Kiểm tra trạng thái đơn hàng sau thanh toán
    order_updated = requests.get(f"{BASE_URL}/orders/{order_id}").json()
    print(f"\n6. Kiểm tra hóa đơn sau gạch nợ:")
    print(f"   -> Trạng thái thanh toán: {order_updated['payment_status']}")
    print(f"   -> Đã thanh toán (net_paid_amount): {order_updated['net_paid_amount']} ₫")
    print(f"   -> Thời gian ghi nhận thanh toán (paid_at): {order_updated['paid_at']}")
    assert order_updated["payment_status"] == "PAID"
    assert float(order_updated["net_paid_amount"]) == 1250000.0
    print("   -> [PASS] Đơn hàng chuyển sang PAID chính xác 100%!")

    # 7. Kiểm tra Báo cáo & Sổ quỹ (dashboard.html)
    dash_updated = requests.get(f"{BASE_URL}/dashboard/summary").json()
    print(f"\n7. Báo cáo Sổ quỹ Dashboard tổng hợp từ dữ liệu thật:")
    print(f"   -> Doanh thu đơn hợp lệ: {dash_updated['valid_order_total']:,.0f} ₫")
    print(f"   -> Thực thu ngân hàng: {dash_updated['total_bank_received']:,.0f} ₫")
    print(f"   -> Tiền đã phân bổ đối soát: {dash_updated['allocated_payment_total']:,.0f} ₫")
    print(f"   -> Còn phải thu: {dash_updated['remaining_receivable']:,.0f} ₫")
    assert dash_updated["valid_order_total"] == 1250000.0
    assert dash_updated["total_bank_received"] == 1250000.0
    assert dash_updated["allocated_payment_total"] == 1250000.0
    assert dash_updated["remaining_receivable"] == 0.0
    print("   -> [PASS] Số liệu Dashboard khớp 100% tuyệt đối với giao dịch thực tế!")

    # 8. Kiểm tra tính toàn vẹn Sổ cái chuỗi băm (Hash-Chain Ledger)
    chain_res = requests.get(f"{BASE_URL}/dashboard/verify-chain").json()
    print(f"\n8. Kiểm tra Sổ cái chuỗi băm (Append-Only Hash Chain):")
    print(f"   -> Trạng thái chuỗi: {chain_res['status']}")
    print(f"   -> Tính toàn vẹn (is_valid): {chain_res['is_valid']}")
    print(f"   -> Số lượng block: {chain_res['total_records']}")
    assert chain_res["is_valid"] is True
    assert chain_res["total_records"] == 1
    first_entry = chain_res["entries"][0]
    print(f"   -> Block #1 Prev Hash: {first_entry['prev_hash']}")
    print(f"   -> Block #1 Record Hash: {first_entry['record_hash']}")
    assert first_entry["prev_hash"] == "GENESIS_00000000000000000000000000000000000000000000000000000000"
    print("   -> [PASS] Chuỗi băm được khởi tạo nối từ Genesis Block hoàn hảo!")

    print("\n=================================================================")
    print("TẤT CẢ 8 BƯỚC KIỂM THỬ QUY TRÌNH THỰC TẾ PRODUCTION ĐỀU PASS 100%!")
    print("=================================================================")

if __name__ == "__main__":
    test_production_real_workflow()
