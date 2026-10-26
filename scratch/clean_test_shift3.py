import sys
import json
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('backend')

from database import SessionLocal
import models

def backup_and_clean_test_shift_3():
    db = SessionLocal()
    try:
        shift3 = db.query(models.Shift).filter(models.Shift.id == 3).first()
        if not shift3:
            print("Shift #3 not found in database. Already clean.")
            return

        print(f"Target Shift to clean: #{shift3.id} - '{shift3.name}'")

        # 1. Collect all target records
        orders = db.query(models.Order).filter(models.Order.shift_id == 3).all()
        order_ids = [o.id for o in orders]
        print(f"Found {len(orders)} orders: {order_ids}")

        requests = db.query(models.PaymentRequest).filter(models.PaymentRequest.order_id.in_(order_ids)).all() if order_ids else []
        req_ids = [r.id for r in requests]
        print(f"Found {len(requests)} payment requests: {req_ids}")

        # Transactions associated with shift 3
        # TX 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 47, 48, 49
        shift3_tx_ids = [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 47, 48, 49]
        txs = db.query(models.BankTransaction).filter(models.BankTransaction.id.in_(shift3_tx_ids)).all()
        print(f"Found {len(txs)} bank transactions: {[t.id for t in txs]}")

        allocs = db.query(models.PaymentAllocation).filter(
            (models.PaymentAllocation.order_id.in_(order_ids)) | 
            (models.PaymentAllocation.bank_transaction_id.in_(shift3_tx_ids))
        ).all() if order_ids or shift3_tx_ids else []
        alloc_ids = [a.id for a in allocs]
        print(f"Found {len(allocs)} payment allocations: {alloc_ids}")

        decs = db.query(models.Decision).filter(
            (models.Decision.order_id.in_(order_ids)) | 
            (models.Decision.bank_transaction_id.in_(shift3_tx_ids))
        ).all() if order_ids or shift3_tx_ids else []
        dec_ids = [d.id for d in decs]
        print(f"Found {len(decs)} decisions: {dec_ids}")

        audits = db.query(models.ShiftAudit).filter(models.ShiftAudit.shift_id == 3).all()
        audit_ids = [a.id for a in audits]
        print(f"Found {len(audits)} shift audits: {audit_ids}")

        # 2. Serialize backup to JSON
        backup_data = {
            "shift": {
                "id": shift3.id,
                "merchant_id": shift3.merchant_id,
                "name": shift3.name,
                "target_revenue": str(shift3.target_revenue),
                "start_time": shift3.start_time.isoformat() if shift3.start_time else None,
                "end_time": shift3.end_time.isoformat() if shift3.end_time else None,
                "closed_at": shift3.closed_at.isoformat() if shift3.closed_at else None,
                "status": str(shift3.status)
            },
            "orders": [
                {
                    "id": o.id,
                    "order_code": o.order_code,
                    "total_amount": str(o.total_amount),
                    "customer_note": o.customer_note,
                    "order_status": str(o.order_status),
                    "payment_status": str(o.payment_status),
                    "created_at": o.created_at.isoformat() if o.created_at else None
                } for o in orders
            ],
            "payment_requests": [
                {
                    "id": r.id,
                    "order_id": r.order_id,
                    "request_code": r.request_code,
                    "expected_amount": str(r.expected_amount),
                    "qr_url": r.qr_url,
                    "status": str(r.status)
                } for r in requests
            ],
            "bank_transactions": [
                {
                    "id": t.id,
                    "reference_code": t.reference_code,
                    "amount": str(t.amount),
                    "allocated_amount": str(t.allocated_amount),
                    "unallocated_amount": str(t.unallocated_amount),
                    "transfer_content": t.transfer_content,
                    "match_status": str(t.match_status)
                } for t in txs
            ],
            "payment_allocations": [
                {
                    "id": a.id,
                    "bank_transaction_id": a.bank_transaction_id,
                    "payment_request_id": a.payment_request_id,
                    "order_id": a.order_id,
                    "entry_type": str(a.entry_type),
                    "allocated_amount": str(a.allocated_amount),
                    "record_hash": a.record_hash,
                    "prev_hash": a.prev_hash
                } for a in allocs
            ],
            "decisions": [
                {
                    "id": d.id,
                    "order_id": d.order_id,
                    "bank_transaction_id": d.bank_transaction_id,
                    "reviewer_id": d.reviewer_id,
                    "decision_type": str(d.decision_type),
                    "reason": d.reason
                } for d in decs
            ],
            "shift_audits": [
                {
                    "id": sa.id,
                    "shift_id": sa.shift_id,
                    "merkle_root": sa.merkle_root,
                    "audit_signature": sa.audit_signature
                } for sa in audits
            ]
        }

        with open("database/backup_deleted_test_shift3.json", "w", encoding="utf-8") as bf:
            json.dump(backup_data, bf, ensure_ascii=False, indent=2)
        print("SUCCESS: Backup saved to database/backup_deleted_test_shift3.json")

        # 3. Perform Deletion in reverse foreign key order
        print("\nDeleting in reverse foreign key order...")
        
        # 3a. Shift Audits
        deleted_audits = db.query(models.ShiftAudit).filter(models.ShiftAudit.shift_id == 3).delete(synchronize_session=False)
        print(f"Deleted {deleted_audits} shift_audits")

        # 3b. Decisions
        if order_ids or shift3_tx_ids:
            deleted_decs = db.query(models.Decision).filter(
                (models.Decision.order_id.in_(order_ids)) | 
                (models.Decision.bank_transaction_id.in_(shift3_tx_ids))
            ).delete(synchronize_session=False)
            print(f"Deleted {deleted_decs} decisions")

        # 3c. Payment Allocations
        if alloc_ids:
            deleted_allocs = db.query(models.PaymentAllocation).filter(
                models.PaymentAllocation.id.in_(alloc_ids)
            ).delete(synchronize_session=False)
            print(f"Deleted {deleted_allocs} payment_allocations")

        # 3d. Payment Requests
        if req_ids:
            deleted_reqs = db.query(models.PaymentRequest).filter(
                models.PaymentRequest.id.in_(req_ids)
            ).delete(synchronize_session=False)
            print(f"Deleted {deleted_reqs} payment_requests")

        # 3e. Orders
        if order_ids:
            deleted_orders = db.query(models.Order).filter(
                models.Order.id.in_(order_ids)
            ).delete(synchronize_session=False)
            print(f"Deleted {deleted_orders} orders")

        # 3f. Bank Transactions
        if shift3_tx_ids:
            deleted_txs = db.query(models.BankTransaction).filter(
                models.BankTransaction.id.in_(shift3_tx_ids)
            ).delete(synchronize_session=False)
            print(f"Deleted {deleted_txs} bank_transactions")

        # 3g. Shift #3
        deleted_shift = db.query(models.Shift).filter(models.Shift.id == 3).delete(synchronize_session=False)
        print(f"Deleted {deleted_shift} shift (Shift #3)")

        db.commit()
        print("\nSUCCESS: All test data for Shift #3 has been permanently cleaned from the database!")

    except Exception as e:
        db.rollback()
        print(f"\nERROR during deletion, rolled back completely: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    backup_and_clean_test_shift_3()
