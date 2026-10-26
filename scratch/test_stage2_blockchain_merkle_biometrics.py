import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import base64
import json
import time
import uuid
import hashlib
import requests
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()
session.headers.update({
    "X-Demo-Role": "OWNER",
    "X-Merchant-Id": "1",
    "X-User-Id": "1"
})

def log_test(step: str, status: str, detail: str = ""):
    icon = "✓" if status == "PASS" else "✗"
    print(f"[{icon}] {step}: {status} {detail}")

def run_stage2_tests():
    print("==================================================================")
    print("BẮT ĐẦU KIỂM THỬ GIAI ĐOẠN 2: BLOCKCHAIN MERKLE TREE & FIDO2 BIOMETRICS")
    print("==================================================================")

    created_shift_ids = []
    created_order_ids = []
    created_tx_refs = []

    try:
        # ------------------------------------------------------------------
        # PHẦN 1: BLOCKCHAIN & REGTECH - CÂY MERKLE CHỐT CA (MERKLE SETTLEMENT)
        # ------------------------------------------------------------------
        now = datetime.now(timezone.utc)
        shift_res = session.post(f"{BASE_URL}/shifts", json={
            "name": f"Ca Merkle Audit {uuid.uuid4().hex[:4]}",
            "target_revenue": 50000000.0,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=8)).isoformat(),
            "status": "OPEN"
        })
        assert shift_res.status_code in [200, 201], f"Failed to create shift: {shift_res.text}"
        shift_data = shift_res.json()
        shift_id = shift_data["id"]
        created_shift_ids.append(shift_id)
        log_test("1a. Shift Setup for Merkle Audit", "PASS", f"Created shift #{shift_id}")

        # 1b. Tạo 3 đơn hàng trong ca
        amounts = [25000.0, 35000.0, 40000.0]
        order_codes = []
        for i, amt in enumerate(amounts):
            code = f"ORD{uuid.uuid4().hex[:4].upper()}"
            order_codes.append(code)
            r_ord = session.post(f"{BASE_URL}/orders", json={
                "shift_id": shift_id,
                "order_code": code,
                "total_amount": amt,
                "customer_note": f"Merkle Test Item {i+1}"
            })
            assert r_ord.status_code == 201, f"Failed create order {code}: {r_ord.text}"
            ord_obj = r_ord.json()
            created_order_ids.append(ord_obj["id"])

            # Thanh toán đầy đủ cho từng đơn hàng
            ref = f"FT_MRK_{uuid.uuid4().hex[:6].upper()}"
            created_tx_refs.append(ref)
            r_tx = session.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
                "reference_code": ref,
                "amount": amt,
                "transfer_content": f"TT {code}"
            })
            assert r_tx.status_code == 200, f"Failed trigger transfer: {r_tx.text}"

        time.sleep(1.0)
        log_test("1b. Order & Allocation Generation", "PASS", f"3 orders paid & allocated: {order_codes}")

        # 1c. Đóng ca làm việc thủ công (quyền OWNER) -> Tự động sinh Merkle Audit Certificate
        close_res = session.post(f"{BASE_URL}/shifts/{shift_id}/close")
        assert close_res.status_code == 200, f"Failed to close shift: {close_res.text}"
        log_test("1c. Shift Close & Audit Trigger", "PASS", f"Shift #{shift_id} closed, Merkle Tree generated")

        # 1d. Truy vấn chứng chỉ kiểm toán Merkle qua API GET /shifts/{id}/merkle-audit
        audit_res = session.get(f"{BASE_URL}/shifts/{shift_id}/merkle-audit")
        assert audit_res.status_code == 200, f"Failed get merkle audit: {audit_res.text}"
        audit = audit_res.json()
        assert audit["merkle_root"] and len(audit["merkle_root"]) == 64, "Invalid Merkle Root length"
        assert audit["total_orders"] == 3
        assert audit["total_revenue"] == 100000.0
        assert audit["total_allocations"] == 3
        assert audit["leaf_count"] == 3
        assert "MERKLE_PROOF_SHIFT_" in audit["audit_signature"]
        log_test("1d. Merkle Root Hash Verification", "PASS", f"Merkle Root: {audit['merkle_root'][:16]}... (3 leaves, 100k revenue)")

        # 1e. Kiểm toán độc lập từng bút toán qua API POST /shifts/{id}/verify-merkle-proof
        for idx, leaf_info in enumerate(audit["leaves"]):
            rec_hash = leaf_info["record_hash"]
            verify_res = session.post(f"{BASE_URL}/shifts/{shift_id}/verify-merkle-proof", json={
                "record_hash": rec_hash
            })
            assert verify_res.status_code == 200, f"Failed verify merkle proof: {verify_res.text}"
            proof_data = verify_res.json()
            assert proof_data["verified"] is True, f"Leaf {idx} verification failed!"
            assert proof_data["merkle_root"] == audit["merkle_root"]
            assert len(proof_data["proof"]) > 0
            log_test(f"1e. Merkle Proof Verification (Leaf #{idx})", "PASS", f"Hash {rec_hash[:12]}... -> Path verified O(log N)")

        # 1f. Kiểm toán phát hiện gian lận (Tampered / Fake Leaf)
        fake_hash = hashlib.sha256(b"FAKE_MODIFIED_TRANSACTION").hexdigest()
        tamper_res = session.post(f"{BASE_URL}/shifts/{shift_id}/verify-merkle-proof", json={
            "record_hash": fake_hash
        })
        assert tamper_res.status_code == 200
        tamper_data = tamper_res.json()
        assert tamper_data["verified"] is False
        log_test("1f. Merkle Tamper Detection", "PASS", f"Fake leaf {fake_hash[:12]}... successfully rejected (verified=False)")

        # ------------------------------------------------------------------
        # PHẦN 2: TRỤ CỘT BIOMETRICS - XÁC THỰC MẬT MÃ HỌC WEBAUTHN FIDO2 (ECDSA P-256)
        # ------------------------------------------------------------------
        # 2a. Sinh cặp khóa ECDSA P-256 mô phỏng phần cứng bảo mật (Secure Enclave / TPM)
        priv_key = ec.generate_private_key(ec.SECP256R1())
        pub_key_pem = priv_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode('utf-8')

        # Cập nhật Public Key cho user 1
        from database import SessionLocal
        import models
        db = SessionLocal()
        test_user = db.query(models.User).filter(models.User.id == 3).first()
        if not test_user:
            test_user = db.query(models.User).first()
        user_id = test_user.id
        test_user.webauthn_public_key = pub_key_pem
        db.commit()
        db.close()
        log_test("2a. FIDO2 ECDSA P-256 Key Registration", "PASS", f"User #{user_id} configured with P-256 public key")

        # 2b. Lấy challenge ngẫu nhiên từ server
        db = SessionLocal()
        user_obj = db.query(models.User).filter(models.User.id == user_id).first()
        from services.webauthn_verifier import generate_user_challenge
        server_challenge = generate_user_challenge(db, user_obj)
        db.close()
        assert len(server_challenge) == 64, "Invalid challenge length"
        log_test("2b. Secure 256-bit Challenge Issuance", "PASS", f"Challenge: {server_challenge[:16]}...")

        # 2c. Chuẩn bị phong bì WebAuthn FIDO2 hợp lệ:
        cdata_dict = {
            "type": "webauthn.get",
            "challenge": server_challenge,
            "origin": "http://localhost:8000"
        }
        cdata_bytes = json.dumps(cdata_dict).encode("utf-8")
        cdata_b64 = base64.b64encode(cdata_bytes).decode("utf-8")

        # AuthenticatorData: rpIdHash (32) + flags (1, UV=0x04, UP=0x01 -> 0x05) + counter (4)
        rp_hash = hashlib.sha256(b"localhost").digest()
        auth_data_bytes = rp_hash + bytes([0x05]) + (1).to_bytes(4, byteorder="big")
        auth_data_b64 = base64.b64encode(auth_data_bytes).decode("utf-8")

        # Ký số mật mã học qua chip bảo mật
        signed_payload = auth_data_bytes + hashlib.sha256(cdata_bytes).digest()
        sig_bytes = priv_key.sign(signed_payload, ec.ECDSA(hashes.SHA256()))
        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

        # Tạo 1 giao dịch ngân hàng cần xử lý ngoại lệ
        ex_ref = f"FT_EX_{uuid.uuid4().hex[:6].upper()}"
        created_tx_refs.append(ex_ref)
        r_ex_tx = session.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": ex_ref,
            "amount": 70000.0,
            "transfer_content": "KHACH CHUYEN SAI NOI DUNG"
        })
        assert r_ex_tx.status_code == 200
        tx_id = r_ex_tx.json().get("transaction_id") or r_ex_tx.json().get("response_data", {}).get("transaction_id")

        # Gửi quyết định ngoại lệ kèm bằng chứng mật mã học WebAuthn FIDO2
        decision_res = session.post(f"{BASE_URL}/decisions", json={
            "reviewer_id": user_id,
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_id,
            "reason": "Xử lý khoản chuyển nhầm có xác thực sinh trắc học",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge_used": server_challenge,
            "assertion_signature": sig_b64,
            "client_data_json": cdata_b64,
            "authenticator_data": auth_data_b64,
            "is_demo": False
        })
        assert decision_res.status_code == 200, f"WebAuthn decision rejected: {decision_res.text}"
        dec_json = decision_res.json()
        assert dec_json.get("biometric_verified") is True
        log_test("2c. WebAuthn FIDO2 Biometric Execution", "PASS", "ECDSA P-256 signature & UV flag accepted 200 OK")

        # 2d. Kiểm tra Chống Replay Attack: Dùng lại cùng Challenge và Signature
        replay_decision_res = session.post(f"{BASE_URL}/decisions", json={
            "reviewer_id": user_id,
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_id,
            "reason": "Thử nghiệm Replay Attack với Challenge cũ",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge_used": server_challenge,
            "assertion_signature": sig_b64,
            "client_data_json": cdata_b64,
            "authenticator_data": auth_data_b64,
            "is_demo": False
        })
        assert replay_decision_res.status_code == 401, f"Expected 401 for Replayed Challenge, got {replay_decision_res.status_code}"
        log_test("2d. Anti-Replay Challenge Invalidation", "PASS", "Replayed challenge rejected with 401 Unauthorized")

        # 2e. Kiểm tra Giả mạo Sinh trắc học: Cố tình bỏ cờ UV (User Verified)
        db = SessionLocal()
        user_obj = db.query(models.User).filter(models.User.id == user_id).first()
        challenge_no_uv = generate_user_challenge(db, user_obj)
        db.close()

        cdata_no_uv = json.dumps({"type": "webauthn.get", "challenge": challenge_no_uv}).encode("utf-8")
        auth_data_no_uv = rp_hash + bytes([0x01]) + (2).to_bytes(4, byteorder="big")
        sig_no_uv = base64.b64encode(priv_key.sign(auth_data_no_uv + hashlib.sha256(cdata_no_uv).digest(), ec.ECDSA(hashes.SHA256()))).decode("utf-8")

        no_uv_res = session.post(f"{BASE_URL}/decisions", json={
            "reviewer_id": user_id,
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_id,
            "reason": "Thử nghiệm không quét vân tay (Thiếu UV)",
            "security_mode": "WEBAUTHN_SIGN",
            "challenge_used": challenge_no_uv,
            "assertion_signature": sig_no_uv,
            "client_data_json": base64.b64encode(cdata_no_uv).decode("utf-8"),
            "authenticator_data": base64.b64encode(auth_data_no_uv).decode("utf-8"),
            "is_demo": False
        })
        assert no_uv_res.status_code == 401
        assert "Thiếu cờ User Verified" in no_uv_res.json()["detail"] or "sinh trắc học" in no_uv_res.json()["detail"].lower()
        log_test("2e. Biometric UV Flag Enforcement", "PASS", "Missing biometric flag rejected: 'Chưa quét sinh trắc học (Thiếu cờ User Verified)'")

        # 2f. Kiểm tra Chế độ Cố tình Bỏ qua WebAuthn (Security Bypass Test TC-06)
        bypass_res = session.post(f"{BASE_URL}/decisions", json={
            "reviewer_id": user_id,
            "decision_type": "OVERPAYMENT_RESOLUTION",
            "bank_transaction_id": tx_id,
            "reason": "Cố tình bỏ qua sinh trắc học",
            "security_mode": "BYPASS_WEBAUTHN_TEST",
            "is_demo": False
        })
        assert bypass_res.status_code == 401
        log_test("2f. Security Bypass Attack Prevention", "PASS", f"Bypass attempt rejected with 401: {bypass_res.json()['detail']}")

        print("==================================================================")
        print("TẤT CẢ CÁC BÀI KIỂM THỬ GIAI ĐOẠN 2 ĐÃ HOÀN TOÀN ĐẠT CHUẨN (ALL PASS)!")
        print("==================================================================")

    finally:
        print("Cleaning up test data...")
        from database import SessionLocal
        import models
        db = SessionLocal()
        try:
            if created_shift_ids:
                db.query(models.ShiftAudit).filter(models.ShiftAudit.shift_id.in_(created_shift_ids)).delete(synchronize_session=False)
            if created_order_ids:
                db.query(models.PaymentAllocation).filter(models.PaymentAllocation.order_id.in_(created_order_ids)).delete(synchronize_session=False)
                db.query(models.PaymentRequest).filter(models.PaymentRequest.order_id.in_(created_order_ids)).delete(synchronize_session=False)
                db.query(models.Order).filter(models.Order.id.in_(created_order_ids)).delete(synchronize_session=False)
            if created_tx_refs:
                db.query(models.Decision).filter(models.Decision.bank_transaction_id.in_(
                    db.query(models.BankTransaction.id).filter(models.BankTransaction.reference_code.in_(created_tx_refs))
                )).delete(synchronize_session=False)
                db.query(models.PaymentAllocation).filter(models.PaymentAllocation.bank_transaction_id.in_(
                    db.query(models.BankTransaction.id).filter(models.BankTransaction.reference_code.in_(created_tx_refs))
                )).delete(synchronize_session=False)
                db.query(models.BankTransaction).filter(models.BankTransaction.reference_code.in_(created_tx_refs)).delete(synchronize_session=False)
            if created_shift_ids:
                db.query(models.Shift).filter(models.Shift.id.in_(created_shift_ids)).delete(synchronize_session=False)
            db.commit()
            print("Cleanup complete!")
        except Exception as e:
            db.rollback()
            print(f"Cleanup error: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    run_stage2_tests()
