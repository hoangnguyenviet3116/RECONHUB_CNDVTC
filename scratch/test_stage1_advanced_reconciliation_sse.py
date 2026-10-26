import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import time
import json
import uuid
import requests
from decimal import Decimal
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def log_test(step: str, status: str, detail: str = ""):
    icon = "✓" if status == "PASS" else "✗"
    print(f"[{icon}] {step}: {status} {detail}")

def run_tests():
    print("==================================================================")
    print("BẮT ĐẦU KIỂM THỬ TÍCH HỢP GIAI ĐOẠN 1: RECONCILIATION & SSE & OPEN BANKING")
    print("==================================================================")

    # 0. Check health
    r = requests.get(f"{BASE_URL}/docs")
    assert r.status_code == 200, "Backend API is not responding"
    log_test("0. API Health Check", "PASS", "Backend responding 200 OK")

    # Get a valid shift or create one if needed
    shifts_res = requests.get(f"{BASE_URL}/shifts")
    shifts = shifts_res.json()
    open_shifts = [s for s in shifts if s.get("status") == "OPEN"]
    
    if open_shifts:
        test_shift_id = open_shifts[0]["id"]
    else:
        create_shift_res = requests.post(f"{BASE_URL}/shifts", json={
            "name": "Ca Thử Nghiệm Đối Soát Nâng Cao",
            "target_revenue": 10000000,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "status": "OPEN"
        })
        assert create_shift_res.status_code in [200, 201], f"Failed to create shift: {create_shift_res.text}"
        test_shift_id = create_shift_res.json()["id"]

    log_test("0. Shift Setup", "PASS", f"Using shift id={test_shift_id}")

    created_order_ids = []
    created_tx_refs = []

    try:
        # ------------------------------------------------------------------
        # TEST 1: TIER 1 - QUANG HỌC & GÕ NHẦM (OPTICAL TYPO COMPENSATION)
        # ------------------------------------------------------------------
        code_1 = f"ORD{uuid.uuid4().hex[:4].upper()}"
        r1 = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": test_shift_id,
            "order_code": code_1,
            "total_amount": 65000.0,
            "customer_note": "Test Typo Optical"
        })
        assert r1.status_code == 201, f"Failed create order 1: {r1.text}"
        ord1 = r1.json()
        created_order_ids.append(ord1["id"])

        # Customer types with space between ORD and code: "TT ORD 1234 CHUYEN TIEN"
        tx1_ref = f"FT_TYPO_{uuid.uuid4().hex[:6].upper()}"
        created_tx_refs.append(tx1_ref)
        
        content_with_space = f"TT {code_1[:3]} {code_1[3:]} CHUYEN TIEN"
        r1_tx = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx1_ref,
            "amount": 65000.0,
            "transfer_content": content_with_space
        })
        assert r1_tx.status_code == 200, f"Failed trigger tx1: {r1_tx.text}"
        
        time.sleep(0.5)
        ord1_chk = requests.get(f"{BASE_URL}/orders/{ord1['id']}").json()
        assert ord1_chk["payment_status"] == "PAID", f"Order status is {ord1_chk['payment_status']}, expected PAID"
        assert float(ord1_chk["remaining_amount"]) == 0.0
        log_test("1. Tier 1 Typo Space/Delimiter Normalization", "PASS", f"{content_with_space} -> Matched {code_1} -> PAID")

        # Optical typo test: e.g. ORD 9OO1 (using letter O instead of 0)
        code_2 = f"ORD9001"
        r2 = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": test_shift_id,
            "order_code": code_2,
            "total_amount": 50000.0,
            "customer_note": "Test Optical O to 0"
        })
        if r2.status_code == 201:
            ord2 = r2.json()
            created_order_ids.append(ord2["id"])
            tx2_ref = f"FT_OPT_{uuid.uuid4().hex[:6].upper()}"
            created_tx_refs.append(tx2_ref)

            # Customer types ORD9OO1 (letters O)
            typo_content = "TT ORD 9OO1 KHACH CHUYEN"
            r2_tx = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
                "reference_code": tx2_ref,
                "amount": 50000.0,
                "transfer_content": typo_content
            })
            assert r2_tx.status_code == 200
            time.sleep(0.5)
            ord2_chk = requests.get(f"{BASE_URL}/orders/{ord2['id']}").json()
            assert ord2_chk["payment_status"] == "PAID"
            assert float(ord2_chk["remaining_amount"]) == 0.0
            log_test("1b. Tier 1 Optical Substitution (O -> 0)", "PASS", f"{typo_content} -> Matched ORD9001 -> PAID")

        # ------------------------------------------------------------------
        # TEST 2: TIER 2 - RAPIDFUZZ MULTI-FACTOR CONFIDENCE SCORING
        # ------------------------------------------------------------------
        code_3 = f"ORD{uuid.uuid4().hex[:4].upper()}"
        r3 = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": test_shift_id,
            "order_code": code_3,
            "total_amount": 85000.0,
            "customer_note": "Ban 09 Ca Phe Muoi"
        })
        assert r3.status_code == 201
        ord3 = r3.json()
        created_order_ids.append(ord3["id"])

        # Transfer content does NOT have order code, but has note "Ban 09 Ca Phe Muoi" and exact amount 85k
        tx3_ref = f"FT_FUZZ_{uuid.uuid4().hex[:6].upper()}"
        created_tx_refs.append(tx3_ref)
        fuzz_content = "KHACH BAN 09 CA PHE MUOI TT"
        r3_tx = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx3_ref,
            "amount": 85000.0,
            "transfer_content": fuzz_content
        })
        assert r3_tx.status_code == 200
        time.sleep(0.5)
        ord3_chk = requests.get(f"{BASE_URL}/orders/{ord3['id']}").json()
        assert ord3_chk["payment_status"] == "PAID", f"Order 3 status is {ord3_chk['payment_status']}"
        assert float(ord3_chk["remaining_amount"]) == 0.0
        log_test("2. Tier 2 RapidFuzz Multi-Factor Matching", "PASS", f"'{fuzz_content}' + 85k -> Matched {code_3} -> PAID")

        # ------------------------------------------------------------------
        # TEST 3: TIER 3 - SUBSET-SUM ENGINE (BUNDLED TRANSFERS)
        # ------------------------------------------------------------------
        code_4a = f"ORD{uuid.uuid4().hex[:4].upper()}"
        code_4b = f"ORD{uuid.uuid4().hex[:4].upper()}"
        
        r4a = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": test_shift_id,
            "order_code": code_4a,
            "total_amount": 33000.0,
            "customer_note": "Bundle Item A"
        })
        r4b = requests.post(f"{BASE_URL}/orders", json={
            "shift_id": test_shift_id,
            "order_code": code_4b,
            "total_amount": 47000.0,
            "customer_note": "Bundle Item B"
        })
        assert r4a.status_code == 201 and r4b.status_code == 201
        ord4a = r4a.json()
        ord4b = r4b.json()
        created_order_ids.extend([ord4a["id"], ord4b["id"]])

        # 1 single transfer for 80,000 (33k + 47k = 80k) with generic bundled content
        tx4_ref = f"FT_BUNDLE_{uuid.uuid4().hex[:6].upper()}"
        created_tx_refs.append(tx4_ref)
        bundle_content = "THANH TOAN GOC 2 BAN"
        r4_tx = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": tx4_ref,
            "amount": 80000.0,
            "transfer_content": bundle_content
        })
        assert r4_tx.status_code == 200
        time.sleep(0.5)

        ord4a_chk = requests.get(f"{BASE_URL}/orders/{ord4a['id']}").json()
        ord4b_chk = requests.get(f"{BASE_URL}/orders/{ord4b['id']}").json()
        assert ord4a_chk["payment_status"] == "PAID", f"Order 4a status: {ord4a_chk['payment_status']}"
        assert ord4b_chk["payment_status"] == "PAID", f"Order 4b status: {ord4b_chk['payment_status']}"
        assert float(ord4a_chk["remaining_amount"]) == 0.0
        assert float(ord4b_chk["remaining_amount"]) == 0.0
        log_test("3. Tier 3 Subset-Sum Bundled Transfer", "PASS", f"1 TX 80,000đ auto-allocated to {code_4a} (33k) and {code_4b} (47k) -> Both PAID")

        # ------------------------------------------------------------------
        # TEST 4: BLOCKCHAIN & REGTECH HASH-CHAIN INTEGRITY
        # ------------------------------------------------------------------
        allocs_res = requests.get(f"{BASE_URL}/allocations")
        if allocs_res.status_code == 200:
            allocs = allocs_res.json()
            assert len(allocs) > 0, "No allocations found"
            last_alloc = allocs[0]
            assert "record_hash" in last_alloc and len(last_alloc["record_hash"]) == 64
            assert "prev_hash" in last_alloc
            log_test("4. Blockchain & RegTech SHA-256 Ledger", "PASS", f"Hash-chain active, latest record_hash={last_alloc['record_hash'][:16]}...")

        # ------------------------------------------------------------------
        # TEST 5: OPEN BANKING SECURITY & ANTI-REPLAY ATTACK
        # ------------------------------------------------------------------
        # 5a: Replay Attack Simulation via test_mode="REPLAY_ATTACK"
        replay_ref = f"FT_REPLAY_{uuid.uuid4().hex[:6].upper()}"
        created_tx_refs.append(replay_ref)
        r_replay = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": replay_ref,
            "amount": 10000.0,
            "transfer_content": "TEST REPLAY ATTACK",
            "test_mode": "REPLAY_ATTACK",
            "simulate_replay_attack": True
        })
        # Should be rejected with 401 Unauthorized because timestamp is 600s old
        assert r_replay.status_code == 401, f"Expected 401 Unauthorized for replay attack, got {r_replay.status_code}: {r_replay.text}"
        log_test("5a. Open Banking Anti-Replay (Timestamp > 300s)", "PASS", f"Old timestamp rejected with 401: {r_replay.json().get('detail')}")

        # 5b: Invalid HMAC Signature
        r_invalid_hmac = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json={
            "reference_code": f"FT_BADHMAC_{uuid.uuid4().hex[:6].upper()}",
            "amount": 10000.0,
            "transfer_content": "TEST BAD HMAC",
            "test_mode": "INVALID_HMAC",
            "tamper_signature": True
        })
        assert r_invalid_hmac.status_code == 401, f"Expected 401 for bad HMAC, got {r_invalid_hmac.status_code}"
        log_test("5b. Open Banking HMAC Verification", "PASS", f"Tampered HMAC rejected with 401: {r_invalid_hmac.json().get('detail')}")

        # ------------------------------------------------------------------
        # TEST 6: REAL-TIME SSE STREAMING (/events/stream)
        # ------------------------------------------------------------------
        import urllib.request
        req = urllib.request.Request(f"{BASE_URL}/events/stream")
        with urllib.request.urlopen(req, timeout=3) as resp:
            content_type = resp.headers.get("Content-Type", "")
            assert "text/event-stream" in content_type, f"Expected text/event-stream, got {content_type}"
            log_test("6. Real-time SSE Endpoint", "PASS", f"Content-Type: {content_type}")

        print("==================================================================")
        print("TẤT CẢ CÁC BÀI KIỂM THỬ GIAI ĐOẠN 1 ĐÃ HOÀN TOÀN ĐẠT CHUẨN (ALL PASS)!")
        print("==================================================================")

    finally:
        # Cleanup test orders and transactions to maintain pristine DB
        print("Cleaning up test orders and transactions...")
        try:
            from database import SessionLocal
            import models
            db = SessionLocal()
            if created_order_ids:
                db.query(models.PaymentAllocation).filter(models.PaymentAllocation.order_id.in_(created_order_ids)).delete(synchronize_session=False)
                db.query(models.PaymentRequest).filter(models.PaymentRequest.order_id.in_(created_order_ids)).delete(synchronize_session=False)
                db.query(models.Order).filter(models.Order.id.in_(created_order_ids)).delete(synchronize_session=False)
            if created_tx_refs:
                db.query(models.BankTransaction).filter(models.BankTransaction.reference_code.in_(created_tx_refs)).delete(synchronize_session=False)
            db.commit()
            print("Cleanup complete!")
            db.close()
        except Exception as e:
            print(f"Cleanup error: {e}")

if __name__ == "__main__":
    run_tests()
