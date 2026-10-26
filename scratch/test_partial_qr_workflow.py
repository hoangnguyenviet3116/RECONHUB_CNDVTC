import sys
import os
import requests
import json
from decimal import Decimal
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {
    "Content-Type": "application/json",
    "X-Merchant-Id": "1",
    "X-User-Id": "1",
    "X-Demo-Role": "OWNER"
}

def run_test():
    print("=== STARTING QA TEST: PARTIAL PAYMENT & REMAINING QR WORKFLOW ===")

    # 1. Check or create an open shift
    shifts_resp = requests.get(f"{BASE_URL}/shifts", headers=HEADERS)
    assert shifts_resp.status_code == 200, f"Failed to list shifts: {shifts_resp.text}"
    shifts = shifts_resp.json()
    open_shifts = [s for s in shifts if s.get("status") == "OPEN"]
    
    created_shift_id = None
    if open_shifts:
        shift_id = open_shifts[0]["id"]
        print(f"[OK] Using existing open shift ID {shift_id}")
    else:
        # Create a shift
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)
        shift_payload = {
            "name": "Ca QA Test",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        create_shift_resp = requests.post(f"{BASE_URL}/shifts", json=shift_payload, headers=HEADERS)
        assert create_shift_resp.status_code in [200, 201], f"Failed to create shift: {create_shift_resp.text}"
        shift_data = create_shift_resp.json()
        shift_id = shift_data["id"]
        created_shift_id = shift_id
        print(f"[OK] Created test shift ID {shift_id}")

    test_order_code = f"ORDQA{int(datetime.now().timestamp()) % 10000}"
    test_order_id = None
    created_tx_ids = []

    try:
        # 2. Create order with total_amount = 200,000 VND
        order_payload = {
            "shift_id": shift_id,
            "order_code": test_order_code,
            "total_amount": 200000,
            "note": "Khách mua bánh & cafe - Test Partial QR"
        }
        order_resp = requests.post(f"{BASE_URL}/orders", json=order_payload, headers=HEADERS)
        assert order_resp.status_code == 201, f"Failed to create order: {order_resp.text}"
        order_data = order_resp.json()
        test_order_id = order_data["id"]
        print(f"[OK] Created Order {test_order_code} (ID: {test_order_id}), Total: 200,000 VND")

        # 3. Issue initial VietQR
        qr_resp = requests.post(f"{BASE_URL}/payment-requests", json={"order_id": test_order_id, "expected_amount": 200000}, headers=HEADERS)
        assert qr_resp.status_code == 201, f"Failed to issue QR: {qr_resp.text}"
        initial_qr = qr_resp.json()
        assert float(initial_qr["expected_amount"]) == 200000.0, f"Initial QR expected amount mismatch: {initial_qr}"
        assert "200000" in initial_qr["qr_url"], f"Initial QR URL does not contain 200000: {initial_qr['qr_url']}"
        print(f"[OK] Initial QR issued: Expected 200,000 VND, URL: {initial_qr['qr_url'][:60]}...")

        # 4. Simulate Customer paying 120,000 VND (Partial payment)
        tx_ref_1 = f"TXN_QA1_{int(datetime.now().timestamp())}"
        transfer_payload_1 = {
            "reference_code": tx_ref_1,
            "amount": 120000,
            "transfer_content": f"TT {test_order_code}",
            "sender_account": "0987654321",
            "test_mode": "STANDARD"
        }
        tx_resp_1 = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json=transfer_payload_1)
        assert tx_resp_1.status_code == 200, f"Failed to trigger bank transfer 1: {tx_resp_1.text}"
        print(f"[OK] Customer transferred 120,000 VND (partial) for {test_order_code}")

        # 5. Check order status & enriched details
        get_orders_resp = requests.get(f"{BASE_URL}/orders", headers=HEADERS)
        assert get_orders_resp.status_code == 200
        all_orders = get_orders_resp.json()
        matched = [o for o in all_orders if o["id"] == test_order_id]
        assert len(matched) == 1, "Order not found in GET /orders"
        order_info = matched[0]

        print(f"Order status: {order_info.get('payment_status')}")
        print(f"Paid amount: {order_info.get('paid_amount')}")
        print(f"Remaining amount: {order_info.get('remaining_amount')}")
        print(f"Active QR: {order_info.get('active_qr')}")

        assert order_info["payment_status"] == "PARTIALLY_PAID", f"Expected PARTIALLY_PAID, got {order_info['payment_status']}"
        assert float(order_info["paid_amount"]) == 120000.0, f"Expected 120,000 paid, got {order_info['paid_amount']}"
        assert float(order_info["remaining_amount"]) == 80000.0, f"Expected 80,000 remaining, got {order_info['remaining_amount']}"

        # 6. Verify that active_qr shows exactly remaining 80,000 VND
        active_qr = order_info.get("active_qr")
        assert active_qr is not None, "active_qr must not be None"
        assert float(active_qr["expected_amount"]) == 80000.0, f"Expected active QR amount 80,000, got {active_qr['expected_amount']}"
        assert "80000" in active_qr["qr_url"], f"QR URL should encode 80000, got {active_qr['qr_url']}"
        print(f"[PASS] Active QR dynamically updated to REMAINING amount: 80,000 VND, URL: {active_qr['qr_url'][:60]}...")

        # 7. Test re-issuing QR or calling /payment-requests explicitly
        qr_resp_2 = requests.post(f"{BASE_URL}/payment-requests", json={"order_id": test_order_id, "expected_amount": 80000}, headers=HEADERS)
        assert qr_resp_2.status_code == 201, f"Failed to issue 2nd QR: {qr_resp_2.text}"
        second_qr = qr_resp_2.json()
        assert float(second_qr["expected_amount"]) == 80000.0, f"Second QR expected amount mismatch: {second_qr}"
        assert "80000" in second_qr["qr_url"], f"Second QR URL does not contain 80000: {second_qr['qr_url']}"
        print(f"[PASS] Re-issued QR explicitly enforces remaining 80,000 VND")

        # 8. Customer pays remaining 80,000 VND
        tx_ref_2 = f"TXN_QA2_{int(datetime.now().timestamp())}"
        transfer_payload_2 = {
            "reference_code": tx_ref_2,
            "amount": 80000,
            "transfer_content": f"TT {test_order_code}",
            "sender_account": "0987654321",
            "test_mode": "STANDARD"
        }
        tx_resp_2 = requests.post(f"{BASE_URL}/mock-bank/trigger-transfer", json=transfer_payload_2)
        assert tx_resp_2.status_code == 200, f"Failed to trigger bank transfer 2: {tx_resp_2.text}"
        print(f"[OK] Customer transferred remaining 80,000 VND")

        # 9. Verify order status is now PAID
        get_orders_resp_final = requests.get(f"{BASE_URL}/orders", headers=HEADERS)
        all_orders_final = get_orders_resp_final.json()
        order_final = [o for o in all_orders_final if o["id"] == test_order_id][0]

        assert order_final["payment_status"] == "PAID", f"Expected PAID, got {order_final['payment_status']}"
        assert float(order_final["paid_amount"]) == 200000.0, f"Expected 200,000 paid, got {order_final['paid_amount']}"
        assert float(order_final["remaining_amount"]) == 0.0, f"Expected 0 remaining, got {order_final['remaining_amount']}"
        print(f"[PASS] Order {test_order_code} is now PAID in full!")

    finally:
        # Clean up all created test data from database
        print("\n--- CLEANING UP TEST DATA FROM DATABASE ---")
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
        from database import SessionLocal
        import models

        db = SessionLocal()
        try:
            if test_order_id:
                # Find allocations
                allocs = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.order_id == test_order_id).all()
                bank_tx_ids = [a.bank_transaction_id for a in allocs]
                for a in allocs:
                    db.delete(a)
                db.commit()

                # Delete payment requests
                qrs = db.query(models.PaymentRequest).filter(models.PaymentRequest.order_id == test_order_id).all()
                for q in qrs:
                    db.delete(q)
                db.commit()

                # Delete order
                ord_obj = db.query(models.Order).filter(models.Order.id == test_order_id).first()
                if ord_obj:
                    db.delete(ord_obj)
                db.commit()

                # Delete bank transactions
                for b_id in bank_tx_ids:
                    bt = db.query(models.BankTransaction).filter(models.BankTransaction.id == b_id).first()
                    if bt:
                        db.delete(bt)
                db.commit()
                print(f"[OK] Cleaned order {test_order_id} and associated transactions & allocations.")

            if created_shift_id:
                shift_obj = db.query(models.Shift).filter(models.Shift.id == created_shift_id).first()
                if shift_obj:
                    db.delete(shift_obj)
                db.commit()
                print(f"[OK] Cleaned test shift {created_shift_id}.")

        except Exception as e:
            print(f"Error during clean up: {e}")
            db.rollback()
        finally:
            db.close()

    print("\n=== QA TEST COMPLETED SUCCESSFULLY! ALL ASSERTIONS PASSED ===")

if __name__ == "__main__":
    run_test()
