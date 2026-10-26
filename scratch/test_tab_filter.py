import sys
import os
import requests
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
    assert opt_resp.status_code == 200
    challenge = opt_resp.json()["challenge"]
    return {
        "challenge": challenge,
        "signature": "DEMO_SIMULATED_SUCCESS_SIGNATURE",
        "credential_id": "CRED_USER_1"
    }

def run_test():
    print("=== TEST: TAB KHOẢN TIỀN CHỜ XỬ LÝ & ẨN GIAO DỊCH ĐÃ XỬ LÝ ===")

    # 1. Check open shift
    shifts_resp = requests.get(f"{BASE_URL}/shifts", headers=HEADERS_OWNER)
    shifts = shifts_resp.json()
    open_shifts = [s for s in shifts if s.get("status") == "OPEN"]
    shift_id = open_shifts[0]["id"] if open_shifts else 1

    tx_ref = f"TXTAB_{int(datetime.now().timestamp())}"
    tx_ids_to_clean = []
    order_ids_to_clean = []

    try:
        # 2. Trigger bank transfer
        tx_resp = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx_ref,
            "amount": 75000,
            "transfer_content": "KHACH HANG CHUYEN NHAM",
            "sender_account": "0911223344",
            "test_mode": "STANDARD"
        })
        assert tx_resp.status_code == 200
        print(f"[OK] Đã tạo giao dịch {tx_ref} (75.000đ)")

        # 3. Query summary
        summary_resp = requests.get(f"{BASE_URL}/dashboard/summary", headers=HEADERS_OWNER)
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        all_txs = summary["bank_transactions"]
        tx_obj = [t for t in all_txs if t["reference_code"] == tx_ref][0]
        tx_ids_to_clean.append(tx_obj["id"])

        # Simulate Tab Filter logic:
        decisions = summary["decisions"]
        
        def filter_pending(tx_list, dec_list):
            return [
                t for t in tx_list
                if not (t.get("is_handled") or any(d.get("bank_transaction_id") == t["id"] for d in dec_list))
                and (t.get("unallocated_amount", 0) > 0 or t.get("match_status") == "UNMATCHED")
            ]

        pending_before = filter_pending(all_txs, decisions)
        assert any(t["id"] == tx_obj["id"] for t in pending_before), "Giao dịch mới PHẢI xuất hiện ở tab Chờ xử lý"
        print(f"[PASS] Giao dịch {tx_ref} xuất hiện trong tab 'Khoản tiền chờ xử lý' trước khi xử lý")

        # 4. Handle transaction
        proof = get_webauthn_proof()
        dec_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_obj["id"],
            "reason": "Khách chuyển nhầm, đã hoàn trả lại tiền mặt",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof["challenge"],
            "signature": proof["signature"],
            "credential_id": proof["credential_id"]
        }, headers=HEADERS_OWNER)
        assert dec_resp.status_code == 200
        print(f"[OK] Đã xử lý giao dịch {tx_ref}")

        # 5. Query summary again
        summary_resp_after = requests.get(f"{BASE_URL}/dashboard/summary", headers=HEADERS_OWNER)
        summary_after = summary_resp_after.json()
        all_txs_after = summary_after["bank_transactions"]
        decisions_after = summary_after["decisions"]

        reloaded_tx = [t for t in all_txs_after if t["id"] == tx_obj["id"]][0]
        assert reloaded_tx["is_handled"] is True, "is_handled phải là True"

        pending_after = filter_pending(all_txs_after, decisions_after)
        assert not any(t["id"] == tx_obj["id"] for t in pending_after), "Giao dịch đã xử lý KHÔNG ĐƯỢC PHÉP xuất hiện ở tab Chờ xử lý nữa!"
        print(f"[PASS] Giao dịch {tx_ref} ĐÃ BIẾN MẤT khỏi tab 'Khoản tiền chờ xử lý' sau khi xử lý thành công!")

        # 6. Verify it appears in History
        hist_matched = [d for d in decisions_after if d.get("bank_transaction_id") == tx_obj["id"]]
        assert len(hist_matched) >= 1
        print(f"[PASS] Giao dịch xuất hiện chính xác trong tab 'Lịch sử phê duyệt'!")

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
                bt = db.query(models.BankTransaction).filter(models.BankTransaction.id == tid).first()
                if bt:
                    db.delete(bt)
            db.commit()
            print("[OK] Đã dọn dẹp sạch sẽ.")
        except Exception as e:
            print(f"Lỗi: {e}")
            db.rollback()
        finally:
            db.close()

    print("\n=== TEST PASSED 100%! ===")

if __name__ == "__main__":
    run_test()
