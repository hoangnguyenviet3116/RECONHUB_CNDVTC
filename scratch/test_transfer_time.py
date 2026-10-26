import os
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests

sys.path.insert(0, os.path.abspath("backend"))

import models
from database import SessionLocal

vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")

def test_transfer_time_accuracy():
    print("=== KIEM THU DO CHINH XAC THOI GIAN CHUYEN KHOAN ===")
    
    # 1. Test case A: Payload truyền transfer_time từ client (khi user bấm nút)
    click_time = datetime.now(vn_tz)
    print(f"1. Gia lap bam nut chuyen khoan tai client luc: {click_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    ref_code_a = f"FTTIME{int(click_time.timestamp())}"
    payload_a = {
        "reference_code": ref_code_a,
        "amount": 2500000.0,
        "transfer_content": "CHUYEN TIEN TEST THOI GIAN A",
        "transfer_time": click_time.isoformat(),
        "transaction_date": click_time.isoformat()
    }
    
    res_a = requests.post("http://127.0.0.1:8000/mock-bank/trigger-transfer", json=payload_a)
    assert res_a.status_code == 200, f"Trigger transfer failed: {res_a.text}"
    print("   -> API /mock-bank/trigger-transfer thanh cong (HTTP 200).")
    
    # Kiểm tra DB cho Test Case A
    db = SessionLocal()
    try:
        tx_a = db.query(models.BankTransaction).filter(models.BankTransaction.reference_code == ref_code_a).first()
        assert tx_a is not None, "Khong tim thay giao dich trong DB"
        
        diff_a = abs((tx_a.created_at - click_time.replace(tzinfo=None)).total_seconds())
        print(f"   -> Thoi gian ghi nhan trong DB: {tx_a.created_at}")
        print(f"   -> Chenh lech so voi thoi gian bam nut: {diff_a:.3f} giay")
        assert diff_a < 3.0, f"LOI: Chenh lech qua lon ({diff_a} giay)! Thoi gian bi lech mui gio!"
        print("   [PASS] Test Case A: Thoi gian giao dich trung khop chinh xac voi thoi gian bam nut!")
        
        # 2. Test case B: Trường hợp payload không gửi kèm transfer_time (Backend tự sinh theo giờ VN)
        server_now_before = datetime.now(vn_tz)
        ref_code_b = f"FTTIMESRV{int(server_now_before.timestamp())}"
        payload_b = {
            "reference_code": ref_code_b,
            "amount": 1800000.0,
            "transfer_content": "CHUYEN TIEN TEST THOI GIAN B"
        }
        res_b = requests.post("http://127.0.0.1:8000/mock-bank/trigger-transfer", json=payload_b)
        assert res_b.status_code == 200, f"Trigger transfer B failed: {res_b.text}"
        
        tx_b = db.query(models.BankTransaction).filter(models.BankTransaction.reference_code == ref_code_b).first()
        assert tx_b is not None, "Khong tim thay giao dich B trong DB"
        diff_b = abs((tx_b.created_at - server_now_before.replace(tzinfo=None)).total_seconds())
        print(f"\n2. Test Case B (Backend fallback gio VN):")
        print(f"   -> Thoi gian server goi API: {server_now_before.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   -> Thoi gian ghi nhan trong DB: {tx_b.created_at}")
        print(f"   -> Chenh lech: {diff_b:.3f} giay")
        assert diff_b < 3.0, f"LOI: Chenh lech qua lon ({diff_b} giay)!"
        print("   [PASS] Test Case B: Backend tu sinh thoi gian Viet Nam chuan xac!")

        # 3. Test case C: Tạo đơn hàng mới, phát hành QR, sau đó bấm chuyển khoản thanh toán
        # Tìm ca đang mở
        open_shift = db.query(models.Shift).filter(models.Shift.status == models.ShiftStatus.OPEN).first()
        assert open_shift is not None, "Can co ca dang mo de test tao don"
        
        ts_suffix = int(datetime.now().timestamp())
        order_code = f"ORD_TIME_{ts_suffix}"
        order_create_res = requests.post("http://127.0.0.1:8000/orders", json={
            "shift_id": open_shift.id,
            "order_code": order_code,
            "total_amount": 550000.0,
            "customer_note": "Test transfer time match"
        })
        assert order_create_res.status_code == 201, f"Create order failed: {order_create_res.text}"
        order_data = order_create_res.json()
        order_id = order_data["id"]
        
        # Phát hành QR cho đơn
        qr_res = requests.post("http://127.0.0.1:8000/payment-requests", json={
            "order_id": order_id,
            "expected_amount": 550000.0
        })
        assert qr_res.status_code == 201, f"Issue QR failed: {qr_res.text}"
        
        # Bấm nút chuyển khoản cho đơn này
        click_c = datetime.now(vn_tz)
        ref_code_c = f"FTTIMEORD{int(click_c.timestamp())}"
        payload_c = {
            "reference_code": ref_code_c,
            "amount": 550000.0,
            "transfer_content": f"TT {order_code}",
            "transfer_time": click_c.isoformat(),
            "transaction_date": click_c.isoformat()
        }
        res_c = requests.post("http://127.0.0.1:8000/mock-bank/trigger-transfer", json=payload_c)
        assert res_c.status_code == 200, f"Trigger transfer C failed: {res_c.text}"
        
        # Gọi API /orders/{id}
        order_res = requests.get(f"http://127.0.0.1:8000/orders/{order_id}").json()
        paid_at_str = order_res.get("paid_at")
        print(f"\n3. Test Case C (Khop don hang {order_code}):")
        print(f"   -> Trang thai thanh toan: {order_res.get('payment_status')}")
        assert order_res.get("payment_status") == "PAID", f"Don hang chua duoc thanh toan: {order_res}"
        print(f"   -> paid_at tu API /orders/{order_id}: {paid_at_str}")
        paid_at_dt = datetime.fromisoformat(paid_at_str)
        diff_c = abs((paid_at_dt - click_c.replace(tzinfo=None)).total_seconds())
        print(f"   -> Chenh lech so voi thoi gian bam chuyen khoan: {diff_c:.3f} giay")
        assert diff_c < 3.0, f"LOI: paid_at bi lech ({diff_c} giay)!"
        print(f"   [PASS] Test Case C: paid_at cua don hang trung khop hoan hao voi thoi diem thanh toan!")

        # 4. Kiểm tra sổ cái chuỗi băm qua API /dashboard/verify-chain
        audit_res = requests.get("http://127.0.0.1:8000/dashboard/verify-chain")
        assert audit_res.status_code == 200, f"Audit endpoint error: {audit_res.text}"
        audit_data = audit_res.json()
        print(f"\n4. Kiem tra tinh toan ven so cai chuoi bam qua /dashboard/verify-chain:")
        print(f"   -> Trang thai: {audit_data.get('status')}")
        print(f"   -> is_valid: {audit_data.get('is_valid')}")
        print(f"   -> message: {audit_data.get('message')}")
        assert audit_data.get("is_valid") is True, f"Chuoi bam bi dut gay: {audit_data.get('message')}"
        print("   [PASS] So cai chuoi bam hoan toan toan ven va hop le!")

    finally:
        db.close()

    print("\n=======================================================")
    print("TAT CA TEST CASE VE THOI GIAN CHUYEN KHOAN DEU DAT 100%!")
    print("=======================================================")

if __name__ == "__main__":
    test_transfer_time_accuracy()
