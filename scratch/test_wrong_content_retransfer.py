import sys
import os
import requests
import json
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"
HEADERS_OWNER = {
    "Content-Type": "application/json",
    "X-Merchant-Id": "1",
    "X-User-Id": "1",
    "X-Demo-Role": "OWNER"
}

def get_webauthn_proof():
    opt_resp = requests.post(f"{BASE_URL}/decisions/webauthn/authenticate/options", headers=HEADERS_OWNER)
    assert opt_resp.status_code == 200, f"Failed to get challenge: {opt_resp.text}"
    challenge = opt_resp.json()["challenge"]
    return {
        "challenge": challenge,
        "signature": "DEMO_SIMULATED_SUCCESS_SIGNATURE",
        "credential_id": "CRED_USER_1"
    }

def run_test():
    print("=== QA TEST: WRONG CONTENT TRANSFER WHEN CUSTOMER TRANSFERS AGAIN (RETRANSFER / OVERPAYMENT) ===")

    # Get shift
    shifts_resp = requests.get(f"{BASE_URL}/shifts", headers=HEADERS_OWNER)
    assert shifts_resp.status_code == 200
    shifts = shifts_resp.json()
    open_shifts = [s for s in shifts if s.get("status") == "OPEN"]
    if open_shifts:
        shift_id = open_shifts[0]["id"]
    else:
        shift_payload = {
            "name": "Ca QA Retransfer",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        }
        create_shift_resp = requests.post(f"{BASE_URL}/shifts", json=shift_payload, headers=HEADERS_OWNER)
        assert create_shift_resp.status_code in [200, 201]
        shift_id = create_shift_resp.json()["id"]

    order_ids_to_clean = []
    tx_ids_to_clean = []

    try:
        # Step 1: Create Order
        ord_code = f"ORDRT{int(datetime.now().timestamp()) % 10000}"
        ord_resp = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": shift_id,
            "order_code": ord_code,
            "total_amount": 50000,
            "note": "Khách mua hàng 50.000đ"
        }, headers=HEADERS_OWNER)
        assert ord_resp.status_code == 201
        order = ord_resp.json()
        order_ids_to_clean.append(order["id"])
        print(f"[OK] 1. Đã tạo đơn {ord_code} (50.000đ)")

        # Step 2: Customer transfers with WRONG content first (Tx1)
        tx_ref_wrong = f"TXW1_{int(datetime.now().timestamp())}"
        tx_resp_1 = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx_ref_wrong,
            "amount": 50000,
            "transfer_content": "KHACH HANG NGUYEN VAN B CHUYEN TIEN",
            "sender_account": "0912345678",
            "test_mode": "STANDARD"
        })
        assert tx_resp_1.status_code == 200
        print(f"[OK] 2. Khách chuyển lần 1 (Tx1: 50.000đ) SAI NỘI DUNG -> Chưa khớp được vào đơn {ord_code}")

        # Step 3: Customer transfers AGAIN with CORRECT content (Tx2)
        tx_ref_correct = f"TXC2_{int(datetime.now().timestamp())}"
        tx_resp_2 = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx_ref_correct,
            "amount": 50000,
            "transfer_content": f"TT {ord_code}",
            "sender_account": "0912345678",
            "test_mode": "STANDARD"
        })
        assert tx_resp_2.status_code == 200
        print(f"[OK] 3. Khách đã chuyển lại lần 2 (Tx2: 50.000đ) ĐÚNG NỘI DUNG 'TT {ord_code}'")

        # Verify order is now PAID
        orders_resp = requests.get(f"{BASE_URL}/orders", headers=HEADERS_OWNER)
        all_orders = orders_resp.json()
        ord_check = [o for o in all_orders if o["id"] == order["id"]][0]
        assert ord_check["payment_status"] == "PAID", f"Order should be PAID, got {ord_check['payment_status']}"
        print(f"[OK] Đơn {ord_code} đã thanh toán đủ (PAID).")

        # Step 4: Check unmatched transactions
        unmatched_resp = requests.get(f"{BASE_URL}/decisions/unmatched-transactions", headers=HEADERS_OWNER)
        assert unmatched_resp.status_code == 200
        unmatched_txs = unmatched_resp.json()

        # Find Tx1
        tx1_obj = [t for t in unmatched_txs if t["reference_code"] == tx_ref_wrong][0]
        tx_ids_to_clean.append(tx1_obj["id"])

        # Find Tx2
        txs_all_resp = requests.get(f"{BASE_URL}/mock-bank/transactions")
        all_bank_txs = txs_all_resp.json()
        tx2_obj = [t for t in all_bank_txs if t["reference_code"] == tx_ref_correct][0]
        tx_ids_to_clean.append(tx2_obj["id"])

        # Step 5: Staff handles Tx1 (tiền chuyển sai nội dung khi khách đã chuyển lại đơn này)
        print(f"\n[TESTING] 4. Nhân viên chọn đơn {ord_code} (đã thu đủ) cho giao dịch chuyển sai Tx1")
        method_note = f"Khách đã chuyển lại qua giao dịch {tx_ref_correct}, khoản chuyển nhầm {tx_ref_wrong} (50.000đ) đã hoàn tiền mặt cho khách tại quầy"
        
        proof = get_webauthn_proof()
        # Test submitting: client sends request with order_id and reason
        decision_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx1_obj["id"],
            "order_id": order["id"],
            "reason": method_note,
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof["challenge"],
            "signature": proof["signature"],
            "credential_id": proof["credential_id"]
        }, headers=HEADERS_OWNER)
        assert decision_resp.status_code == 200, f"Failed: {decision_resp.text}"
        res_data = decision_resp.json()
        assert res_data["status"] == "success"
        print(f"[PASS] Giao dịch sai nội dung đã được xử lý THÀNH CÔNG như một đơn chuyển thừa: {res_data['message']}")

        # Step 6: Verify Persistence and History
        reload_tx_resp = requests.get(f"{BASE_URL}/decisions/unmatched-transactions", headers=HEADERS_OWNER)
        reloaded_tx1 = [t for t in reload_tx_resp.json() if t["id"] == tx1_obj["id"]][0]
        assert reloaded_tx1["is_handled"] is True, "Tx1 must be marked as handled"
        assert float(reloaded_tx1["unallocated_amount"]) == 50000.0, "Unallocated amount must remain intact"
        print(f"[PASS] Sau khi lưu: is_handled = True (nút chuyển thành 'Đã xử lý'), số tiền chưa phân bổ (50.000đ) được giữ nguyên chính xác")

        # Step 7: Check decisions history
        hist_resp = requests.get(f"{BASE_URL}/decisions", headers=HEADERS_OWNER)
        hist = hist_resp.json()
        matched_hist = [h for h in hist if h.get("bank_transaction_id") == tx1_obj["id"]]
        assert len(matched_hist) >= 1
        h_rec = matched_hist[0]
        assert h_rec["decision_type"] == "OVERPAYMENT_RESOLUTION"
        assert h_rec["order_code"] == ord_code
        assert float(h_rec["tx_amount"]) == 50000.0
        assert h_rec["reason"] == method_note
        print(f"[PASS] Lịch sử phê duyệt hiển thị: Loại '{h_rec['decision_type']}' cho đơn {h_rec['order_code']}, số tiền {h_rec['tx_amount']}, lý do: '{h_rec['reason']}'")

    finally:
        print("\n--- DỌN DẸP DỮ LIỆU TEST ---")
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
        from database import SessionLocal
        import models

        db = SessionLocal()
        try:
            for tid in tx_ids_to_clean:
                decs = db.query(models.Decision).filter(models.Decision.bank_transaction_id == tid).all()
                for d in decs:
                    db.delete(d)
            db.commit()

            for oid in order_ids_to_clean:
                allocs = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.order_id == oid).all()
                for a in allocs:
                    db.delete(a)
            db.commit()

            for oid in order_ids_to_clean:
                qrs = db.query(models.PaymentRequest).filter(models.PaymentRequest.order_id == oid).all()
                for q in qrs:
                    db.delete(q)
            db.commit()

            for oid in order_ids_to_clean:
                ord_o = db.query(models.Order).filter(models.Order.id == oid).first()
                if ord_o:
                    db.delete(ord_o)
            db.commit()

            for tid in tx_ids_to_clean:
                bt = db.query(models.BankTransaction).filter(models.BankTransaction.id == tid).first()
                if bt:
                    db.delete(bt)
            db.commit()
            print("[OK] Đã dọn dẹp sạch sẽ toàn bộ dữ liệu test.")
        except Exception as e:
            print(f"Lỗi khi dọn dẹp: {e}")
            db.rollback()
        finally:
            db.close()

    print("\n=== KIỂM THỬ THÀNH CÔNG 100%! ===")

if __name__ == "__main__":
    run_test()
