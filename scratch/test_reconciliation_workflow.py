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
HEADERS_CASHIER = {
    "Content-Type": "application/json",
    "X-Merchant-Id": "1",
    "X-User-Id": "2",
    "X-Demo-Role": "CASHIER"
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

def run_tests():
    print("=== STARTING QA TEST SUITE: RECONCILIATION EXCEPTION & OVERPAYMENT HANDLING ===")

    # Setup shift
    shifts_resp = requests.get(f"{BASE_URL}/shifts", headers=HEADERS_OWNER)
    assert shifts_resp.status_code == 200
    shifts = shifts_resp.json()
    open_shifts = [s for s in shifts if s.get("status") == "OPEN"]
    if open_shifts:
        shift_id = open_shifts[0]["id"]
    else:
        shift_payload = {
            "name": "Ca QA Reconciliation",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        }
        create_shift_resp = requests.post(f"{BASE_URL}/shifts", json=shift_payload, headers=HEADERS_OWNER)
        assert create_shift_resp.status_code in [200, 201]
        shift_id = create_shift_resp.json()["id"]

    order_ids_to_clean = []
    tx_ids_to_clean = []

    try:
        # =====================================================================
        # CASE 1: WRONG CONTENT (Sai nội dung / Chờ ghép đơn)
        # =====================================================================
        print("\n--- TEST 1: CHUYỂN KHOẢN SAI NỘI DUNG ---")
        ord_code_1 = f"ORDW{int(datetime.now().timestamp()) % 10000}"
        ord_resp_1 = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": shift_id,
            "order_code": ord_code_1,
            "total_amount": 60000,
            "note": "Đơn test sai nội dung"
        }, headers=HEADERS_OWNER)
        assert ord_resp_1.status_code == 201
        order_1 = ord_resp_1.json()
        order_ids_to_clean.append(order_1["id"])
        print(f"[OK] Đã tạo đơn {ord_code_1} (60.000đ)")

        # Simulate customer transferring 60,000 VND with wrong content
        tx_ref_1 = f"TXW_{int(datetime.now().timestamp())}"
        tx_resp_1 = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx_ref_1,
            "amount": 60000,
            "transfer_content": "NGUYEN VAN A CHUYEN TIEN MUA HANG",
            "sender_account": "0123456789",
            "test_mode": "STANDARD"
        })
        assert tx_resp_1.status_code == 200
        print(f"[OK] Khách đã chuyển 60.000đ với nội dung sai: 'NGUYEN VAN A CHUYEN TIEN MUA HANG'")

        # Query unmatched-transactions
        unmatched_resp = requests.get(f"{BASE_URL}/decisions/unmatched-transactions", headers=HEADERS_OWNER)
        assert unmatched_resp.status_code == 200
        unmatched_txs = unmatched_resp.json()
        matched_tx_1 = [t for t in unmatched_txs if t["reference_code"] == tx_ref_1]
        assert len(matched_tx_1) == 1, "Giao dịch không xuất hiện trong danh sách chờ ghép"
        tx_obj_1 = matched_tx_1[0]
        tx_ids_to_clean.append(tx_obj_1["id"])
        
        assert tx_obj_1["is_overpayment"] is False, "Giao dịch sai nội dung không được nhận diện nhầm là chuyển thừa"
        assert tx_obj_1["is_handled"] is False, "Giao dịch mới chưa thể có trạng thái đã xử lý"
        print(f"[PASS] Giao dịch được phân loại chính xác: is_overpayment = False, is_handled = False")

        # Test validation: cannot allocate more than unallocated or order remaining
        proof1 = get_webauthn_proof()
        invalid_match_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "APPROVE_MANUAL_MATCH",
            "bank_transaction_id": tx_obj_1["id"],
            "order_id": order_1["id"],
            "allocated_amount": 100000,
            "reason": "Test vượt số tiền",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof1["challenge"],
            "signature": proof1["signature"],
            "credential_id": proof1["credential_id"]
        }, headers=HEADERS_OWNER)
        assert invalid_match_resp.status_code == 400
        print(f"[PASS] Chặn phân bổ vượt quá số tiền chưa phân bổ (400 Bad Request): {invalid_match_resp.json()['detail']}")

        # Perform manual match with correct amount
        proof2 = get_webauthn_proof()
        match_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "APPROVE_MANUAL_MATCH",
            "bank_transaction_id": tx_obj_1["id"],
            "order_id": order_1["id"],
            "allocated_amount": 60000,
            "reason": "Khách hàng xác nhận chuyển khoản nhưng quên ghi mã đơn ORD",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof2["challenge"],
            "signature": proof2["signature"],
            "credential_id": proof2["credential_id"]
        }, headers=HEADERS_OWNER)
        assert match_resp.status_code == 200, f"Match failed: {match_resp.text}"
        print(f"[PASS] Ghép tiền vào hóa đơn thành công! (200 OK)")

        # Verify decision history
        decisions_resp = requests.get(f"{BASE_URL}/decisions", headers=HEADERS_OWNER)
        assert decisions_resp.status_code == 200
        all_decisions = decisions_resp.json()
        match_dec = [d for d in all_decisions if d.get("bank_transaction_id") == tx_obj_1["id"]]
        assert len(match_dec) >= 1
        assert match_dec[0]["decision_type"] == "APPROVE_MANUAL_MATCH"
        assert match_dec[0]["order_code"] == ord_code_1
        assert float(match_dec[0]["tx_amount"]) == 60000.0
        print(f"[PASS] Bản ghi xuất hiện đầy đủ trong Lịch sử phê duyệt với mã đơn {ord_code_1}")


        # =====================================================================
        # CASE 2: OVERPAYMENT (Chuyển thừa tiền)
        # =====================================================================
        print("\n--- TEST 2: GIAO DỊCH CHUYỂN THỪA TIỀN ---")
        ord_code_2 = f"ORDO{int(datetime.now().timestamp()) % 10000}"
        ord_resp_2 = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": shift_id,
            "order_code": ord_code_2,
            "total_amount": 40000,
            "note": "Đơn bánh mì 40.000đ"
        }, headers=HEADERS_OWNER)
        assert ord_resp_2.status_code == 201
        order_2 = ord_resp_2.json()
        order_ids_to_clean.append(order_2["id"])
        print(f"[OK] Đã tạo đơn {ord_code_2} giá trị 40.000đ")

        # Customer transfers 50,000 VND (overpaid by 10,000 VND)
        tx_ref_2 = f"TXO_{int(datetime.now().timestamp())}"
        tx_resp_2 = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx_ref_2,
            "amount": 50000,
            "transfer_content": f"TT {ord_code_2}",
            "sender_account": "0987654321",
            "test_mode": "STANDARD"
        })
        assert tx_resp_2.status_code == 200
        print(f"[OK] Khách đã chuyển 50.000đ cho đơn 40.000đ ({ord_code_2})")

        # Query unmatched-transactions
        unmatched_resp_2 = requests.get(f"{BASE_URL}/decisions/unmatched-transactions", headers=HEADERS_OWNER)
        unmatched_txs_2 = unmatched_resp_2.json()
        matched_tx_2 = [t for t in unmatched_txs_2 if t["reference_code"] == tx_ref_2]
        assert len(matched_tx_2) == 1, "Giao dịch chuyển thừa không xuất hiện trong danh sách đối soát"
        tx_obj_2 = matched_tx_2[0]
        tx_ids_to_clean.append(tx_obj_2["id"])

        print(f"Transaction details: Total: {tx_obj_2['amount']}, Allocated: {tx_obj_2['allocated_amount']}, Unallocated: {tx_obj_2['unallocated_amount']}")
        assert float(tx_obj_2["amount"]) == 50000.0
        assert float(tx_obj_2["allocated_amount"]) == 40000.0
        assert float(tx_obj_2["unallocated_amount"]) == 10000.0
        assert tx_obj_2["order_code"] == ord_code_2
        assert tx_obj_2["is_overpayment"] is True, "Giao dịch PHẢI được nhận diện là chuyển thừa"
        assert tx_obj_2["is_handled"] is False, "Giao dịch chuyển thừa mới chưa thể có trạng thái đã xử lý"
        print(f"[PASS] Giao dịch được xác định chính xác là CHUYỂN THỪA (is_overpayment = True, thừa: 10.000đ)")


        # =====================================================================
        # TEST 3: Validation - Empty method is rejected
        # =====================================================================
        print("\n--- TEST 3: KIỂM TRA BẮT BUỘC NHẬP PHƯƠNG THỨC XỬ LÝ ---")
        proof3 = get_webauthn_proof()
        empty_reason_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_obj_2["id"],
            "order_id": order_2["id"],
            "reason": "   ",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof3["challenge"],
            "signature": proof3["signature"],
            "credential_id": proof3["credential_id"]
        }, headers=HEADERS_OWNER)
        assert empty_reason_resp.status_code == 400
        print(f"[PASS] Hệ thống từ chối khi để trống phương thức xử lý (400 Bad Request): {empty_reason_resp.json()['detail']}")


        # =====================================================================
        # TEST 4: Permission Check - Cashier cannot approve
        # =====================================================================
        print("\n--- TEST 4: KIỂM TRA PHÂN QUYỀN (CASHIER KHÔNG ĐƯỢC PHÊ DUYỆT) ---")
        proof4 = get_webauthn_proof()
        cashier_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_obj_2["id"],
            "order_id": order_2["id"],
            "reason": "Hoàn tiền mặt 10.000đ",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof4["challenge"],
            "signature": proof4["signature"],
            "credential_id": proof4["credential_id"]
        }, headers=HEADERS_CASHIER)
        assert cashier_resp.status_code == 403
        print(f"[PASS] Chặn CASHIER thực hiện phê duyệt ngoại lệ (403 Forbidden): {cashier_resp.json()['detail']}")


        # =====================================================================
        # TEST 5 & 8: Successful Overpayment Recording & Unallocated retention
        # =====================================================================
        print("\n--- TEST 5: XÁC NHẬN PHƯƠNG THỨC XỬ LÝ TIỀN THỪA THÀNH CÔNG ---")
        handling_method_text = "Đã hoàn trả tiền mặt 10.000đ trực tiếp cho khách tại quầy thu ngân"
        proof5 = get_webauthn_proof()
        ovp_success_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_obj_2["id"],
            "order_id": order_2["id"],
            "reason": handling_method_text,
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof5["challenge"],
            "signature": proof5["signature"],
            "credential_id": proof5["credential_id"]
        }, headers=HEADERS_OWNER)
        assert ovp_success_resp.status_code == 200, f"Failed: {ovp_success_resp.text}"
        ovp_data = ovp_success_resp.json()
        assert ovp_data["status"] == "success"
        print(f"[PASS] Backend xác nhận lưu thành công phương thức xử lý tiền thừa: {ovp_data['message']}")


        # =====================================================================
        # TEST 6: Duplicate Submission Prevention
        # =====================================================================
        print("\n--- TEST 6: CHỐNG XỬ LÝ TRÙNG LẶP (DUPLICATE SUBMISSION) ---")
        proof6 = get_webauthn_proof()
        dup_resp = requests.post(f"{BASE_URL}/decisions", json={
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_obj_2["id"],
            "order_id": order_2["id"],
            "reason": "Cố gắng gửi trùng lặp",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge": proof6["challenge"],
            "signature": proof6["signature"],
            "credential_id": proof6["credential_id"]
        }, headers=HEADERS_OWNER)
        assert dup_resp.status_code == 409, f"Expected 409 Conflict, got {dup_resp.status_code}"
        print(f"[PASS] Hệ thống chặn xử lý trùng lặp với mã 409 Conflict: {dup_resp.json()['detail']}")


        # =====================================================================
        # TEST 7: Page Reload Persistence & Unallocated Retention Verification
        # =====================================================================
        print("\n--- TEST 7: KIỂM TRA LƯU TRỮ VÀ GIỮ NGUYÊN TRẠNG THÁI KHI TẢI LẠI TRANG ---")
        reload_txs_resp = requests.get(f"{BASE_URL}/decisions/unmatched-transactions", headers=HEADERS_OWNER)
        assert reload_txs_resp.status_code == 200
        reloaded_tx = [t for t in reload_txs_resp.json() if t["reference_code"] == tx_ref_2][0]

        # Requirement 4 & 7: is_handled must be TRUE on fresh query
        assert reloaded_tx["is_handled"] is True, "Trạng thái đã xử lý không được lưu giữ trên backend"
        assert reloaded_tx["handling_method"] == handling_method_text

        # Requirement 3 & 8: unallocated amount must NOT be wiped or auto-refunded
        assert float(reloaded_tx["unallocated_amount"]) == 10000.0, f"Unallocated amount was incorrectly changed: {reloaded_tx['unallocated_amount']}"
        print(f"[PASS] Khi tải lại trang: is_handled = True, số tiền thừa vẫn giữ nguyên chính xác 10.000đ")

        # Check Lịch sử phê duyệt (Decisions history)
        history_resp = requests.get(f"{BASE_URL}/decisions", headers=HEADERS_OWNER)
        assert history_resp.status_code == 200
        all_hist = history_resp.json()
        ovp_hist = [h for h in all_hist if h.get("bank_transaction_id") == tx_obj_2["id"] and h.get("decision_type") == "OVERPAYMENT_RESOLUTION"]
        assert len(ovp_hist) == 1
        h_item = ovp_hist[0]
        assert h_item["decision_type"] == "OVERPAYMENT_RESOLUTION"
        assert h_item["order_code"] == ord_code_2
        assert float(h_item["tx_amount"]) == 50000.0
        assert float(h_item["allocated_amount"]) == 40000.0
        assert float(h_item["unallocated_amount"]) == 10000.0
        assert h_item["reason"] == handling_method_text
        assert h_item["biometric_verified"] is True
        print(f"[PASS] Lịch sử phê duyệt hiển thị đầy đủ thông tin: GD {h_item['reference_code']}, Đơn {h_item['order_code']}, Tổng {h_item['tx_amount']}, Đã phân bổ {h_item['allocated_amount']}, Tiền thừa {h_item['unallocated_amount']}, Phương thức: {h_item['reason']}")

    finally:
        # Clean up created test data
        print("\n--- DỌN DẸP DỮ LIỆU KIỂM THỬ KHỎI CƠ SỞ DỮ LIỆU ---")
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

            print(f"[OK] Đã dọn dẹp sạch sẽ toàn bộ các bản ghi kiểm thử trong DB.")
        except Exception as e:
            print(f"Lỗi khi dọn dẹp: {e}")
            db.rollback()
        finally:
            db.close()

    print("\n=== TOÀN BỘ 10 KỊCH BẢN KIỂM THỬ ĐÃ VƯỢT QUA 100% THÀNH CÔNG! ===")

if __name__ == "__main__":
    run_tests()
