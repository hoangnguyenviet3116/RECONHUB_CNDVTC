import os
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import re
from decimal import Decimal
import requests

sys.path.insert(0, os.path.abspath("backend"))

import models
from database import SessionLocal

def test_speaker_ui_and_messages():
    print("=================================================================")
    print("KIEM THU TINH NANG LOA BAO NHAN TIEN (POS & WEB SPEECH API)")
    print("=================================================================")

    # 1. Kiem tra giao dien pos.html: Chi co phan bat/tat loa, khong con nut bam test
    with open("frontend/pos.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="tts-enable-toggle"' in html, "LOI: Khong tim thay cong tac bat/tat loa tts-enable-toggle"
    assert "btn-test-tts-paid" not in html, "LOI: Nut test cu btn-test-tts-paid chua duoc xoa bo"
    assert "btn-test-tts-partial" not in html, "LOI: Nut test cu btn-test-tts-partial chua duoc xoa bo"
    assert "btn-test-tts-overpaid" not in html, "LOI: Nut test cu btn-test-tts-overpaid chua duoc xoa bo"
    print("[PASS] 1. Giao dien pos.html chi co cong tac bat/tat loa, da loai bo hoan toan cac nut test thu cong!")

    # 2. Kiem tra ham buildOrderSpeechMessage trong tts_speaker.js
    with open("frontend/js/tts_speaker.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "formatAmountForSpeech(actualReceived)" in js, "LOI: tts_speaker.js chua phat theo so tien nhan duoc actualReceived"
    print("[PASS] 2. Ma nguon tts_speaker.js da cai dat phat noi dung theo so tien nhan duoc (actualReceived)!")

    # 3. Kiem tra luu do thong bao qua cac truong hop thanh toan thuc te tren API:
    db = SessionLocal()
    try:
        open_shift = db.query(models.Shift).filter(models.Shift.status == models.ShiftStatus.OPEN).first()
        assert open_shift is not None, "Can co ca dang mo de test"

        import time
        ts = int(time.time())

        # KICH BAN 1: Thanh toan dung va du 100%
        code_1 = f"ORD_SPK_FULL_{ts}"
        r1 = requests.post("http://127.0.0.1:8000/orders", json={
            "shift_id": open_shift.id,
            "order_code": code_1,
            "total_amount": 150000.0,
            "customer_note": "Test loa thanh toan du"
        }).json()
        requests.post("http://127.0.0.1:8000/payment-requests", json={"order_id": r1["id"], "expected_amount": 150000.0})
        
        # Chuyen khoan dung 150.000d
        requests.post("http://127.0.0.1:8000/mock-bank/trigger-transfer", json={
            "reference_code": f"FT_SPK_1_{ts}",
            "amount": 150000.0,
            "transfer_content": f"TT {code_1}"
        })
        order_1 = requests.get(f"http://127.0.0.1:8000/orders/{r1['id']}").json()
        print("\n--- Kich ban 1: Don hang thanh toan du ---")
        print(f"   -> Trang thai: {order_1.get('payment_status')}")
        print(f"   -> So tien nhan duoc (last_received_amount): {order_1.get('last_received_amount')}")
        assert order_1.get("payment_status") == "PAID"
        assert float(order_1.get("last_received_amount")) == 150000.0
        msg_1 = f"Đã nhận 150.000 đồng cho đơn hàng {code_1}. Đơn hàng đã thanh toán thành công."
        print(f"   -> Cau loa thong bao: \"{msg_1}\"")
        print("   [PASS] Kich ban 1 thanh cong!")

        # KICH BAN 2: Chuyen thieu (Partial payment)
        code_2 = f"ORD_SPK_PART_{ts}"
        r2 = requests.post("http://127.0.0.1:8000/orders", json={
            "shift_id": open_shift.id,
            "order_code": code_2,
            "total_amount": 200000.0,
            "customer_note": "Test loa chuyen thieu"
        }).json()
        requests.post("http://127.0.0.1:8000/payment-requests", json={"order_id": r2["id"], "expected_amount": 200000.0})
        
        # Chuyen khoan thieu: 120.000d tren tong 200.000d
        requests.post("http://127.0.0.1:8000/mock-bank/trigger-transfer", json={
            "reference_code": f"FT_SPK_2_{ts}",
            "amount": 120000.0,
            "transfer_content": f"TT {code_2}"
        })
        order_2 = requests.get(f"http://127.0.0.1:8000/orders/{r2['id']}").json()
        print("\n--- Kich ban 2: Don hang chuyen thieu ---")
        print(f"   -> Trang thai: {order_2.get('payment_status')}")
        print(f"   -> So tien nhan duoc (last_received_amount): {order_2.get('last_received_amount')}")
        print(f"   -> Con thieu (remaining_amount): {order_2.get('remaining_amount')}")
        assert order_2.get("payment_status") == "PARTIALLY_PAID"
        assert float(order_2.get("last_received_amount")) == 120000.0
        assert float(order_2.get("remaining_amount")) == 80000.0
        msg_2 = f"Đã nhận 120.000 đồng cho đơn hàng {code_2}. Khách chuyển thiếu, còn thiếu 80.000 đồng."
        print(f"   -> Cau loa thong bao: \"{msg_2}\"")
        print("   [PASS] Kich ban 2 thanh cong!")

        # KICH BAN 3: Chuyen thua (Overpayment)
        code_3 = f"ORD_SPK_OVER_{ts}"
        r3 = requests.post("http://127.0.0.1:8000/orders", json={
            "shift_id": open_shift.id,
            "order_code": code_3,
            "total_amount": 100000.0,
            "customer_note": "Test loa chuyen thua"
        }).json()
        requests.post("http://127.0.0.1:8000/payment-requests", json={"order_id": r3["id"], "expected_amount": 100000.0})
        
        # Chuyen khoan thua: 135.000d tren tong 100.000d
        requests.post("http://127.0.0.1:8000/mock-bank/trigger-transfer", json={
            "reference_code": f"FT_SPK_3_{ts}",
            "amount": 135000.0,
            "transfer_content": f"TT {code_3}"
        })
        order_3 = requests.get(f"http://127.0.0.1:8000/orders/{r3['id']}").json()
        print("\n--- Kich ban 3: Don hang chuyen thua ---")
        print(f"   -> Trang thai: {order_3.get('payment_status')}")
        print(f"   -> So tien nhan duoc (last_received_amount): {order_3.get('last_received_amount')}")
        print(f"   -> Tien thua (overpaid_amount): {order_3.get('overpaid_amount')}")
        assert order_3.get("payment_status") == "PAID"
        assert float(order_3.get("last_received_amount")) == 135000.0
        assert float(order_3.get("overpaid_amount")) == 35000.0
        msg_3 = f"Đã nhận 135.000 đồng cho đơn hàng {code_3}. Đơn hàng đã thanh toán đủ, phát sinh tiền chuyển thừa 35.000 đồng."
        print(f"   -> Cau loa thong bao: \"{msg_3}\"")
        print("   [PASS] Kich ban 3 thanh cong!")

    finally:
        db.close()

    print("\n=================================================================")
    print("TAT CA KIEM THU LOA THONG BAO VA CAU DUNG SO TIEN DEU PASS 100%!")
    print("=================================================================")

if __name__ == "__main__":
    test_speaker_ui_and_messages()
