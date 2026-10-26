import sys
import json
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('backend')

from database import SessionLocal
import models

def backup_and_clean_all_shifts():
    db = SessionLocal()
    try:
        shifts = db.query(models.Shift).all()
        orders = db.query(models.Order).all()
        requests = db.query(models.PaymentRequest).all()
        transactions = db.query(models.BankTransaction).all()
        allocations = db.query(models.PaymentAllocation).all()
        decisions = db.query(models.Decision).all()
        audits = db.query(models.ShiftAudit).all()

        print(f"Current counts before cleaning:")
        print(f" - Shifts: {len(shifts)}")
        print(f" - Orders: {len(orders)}")
        print(f" - Payment Requests: {len(requests)}")
        print(f" - Bank Transactions: {len(transactions)}")
        print(f" - Payment Allocations: {len(allocations)}")
        print(f" - Decisions: {len(decisions)}")
        print(f" - Shift Audits: {len(audits)}")

        # 1. Backup all data to JSON
        backup_data = {
            "shifts": [
                {
                    "id": s.id,
                    "merchant_id": s.merchant_id,
                    "name": s.name,
                    "target_revenue": str(s.target_revenue),
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "closed_at": s.closed_at.isoformat() if s.closed_at else None,
                    "status": str(s.status)
                } for s in shifts
            ],
            "orders": [
                {
                    "id": o.id,
                    "shift_id": o.shift_id,
                    "created_by": o.created_by,
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
                    "merchant_id": t.merchant_id,
                    "reference_code": t.reference_code,
                    "amount": str(t.amount),
                    "allocated_amount": str(t.allocated_amount),
                    "unallocated_amount": str(t.unallocated_amount),
                    "transfer_content": t.transfer_content,
                    "match_status": str(t.match_status),
                    "created_at": t.created_at.isoformat() if t.created_at else None
                } for t in transactions
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
                    "prev_hash": a.prev_hash,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                } for a in allocations
            ],
            "decisions": [
                {
                    "id": d.id,
                    "order_id": d.order_id,
                    "bank_transaction_id": d.bank_transaction_id,
                    "reviewer_id": d.reviewer_id,
                    "decision_type": str(d.decision_type),
                    "reason": d.reason,
                    "created_at": d.review_date.isoformat() if d.review_date else None
                } for d in decisions
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

        with open("database/backup_deleted_shifts_1_and_2.json", "w", encoding="utf-8") as bf:
            json.dump(backup_data, bf, ensure_ascii=False, indent=2)
        print("\nSUCCESS: Backup created at database/backup_deleted_shifts_1_and_2.json")

        # 2. Delete in exact reverse foreign key dependency order
        print("\nDeleting transaction and shift data...")

        # 2a. shift_audits
        del_audits = db.query(models.ShiftAudit).delete(synchronize_session=False)
        print(f"Deleted {del_audits} shift_audits")

        # 2b. decisions
        del_decs = db.query(models.Decision).delete(synchronize_session=False)
        print(f"Deleted {del_decs} decisions")

        # 2c. payment_allocations
        del_allocs = db.query(models.PaymentAllocation).delete(synchronize_session=False)
        print(f"Deleted {del_allocs} payment_allocations")

        # 2d. payment_requests
        del_reqs = db.query(models.PaymentRequest).delete(synchronize_session=False)
        print(f"Deleted {del_reqs} payment_requests")

        # 2e. orders
        del_orders = db.query(models.Order).delete(synchronize_session=False)
        print(f"Deleted {del_orders} orders")

        # 2f. bank_transactions
        del_txs = db.query(models.BankTransaction).delete(synchronize_session=False)
        print(f"Deleted {del_txs} bank_transactions")

        # 2g. shifts
        del_shifts = db.query(models.Shift).delete(synchronize_session=False)
        print(f"Deleted {del_shifts} shifts")

        db.commit()
        print("\nSUCCESS: All shifts and transactional data have been permanently deleted.")

        # 3. Verify final state
        print("\n=== FINAL VERIFICATION ===")
        print("Remaining Shifts:", db.query(models.Shift).count())
        print("Remaining Orders:", db.query(models.Order).count())
        print("Remaining Payment Requests:", db.query(models.PaymentRequest).count())
        print("Remaining Bank Transactions:", db.query(models.BankTransaction).count())
        print("Remaining Payment Allocations:", db.query(models.PaymentAllocation).count())
        print("Remaining Decisions:", db.query(models.Decision).count())
        print("Remaining Shift Audits:", db.query(models.ShiftAudit).count())
        print("Preserved Users:", db.query(models.User).count())
        print("Preserved Merchants:", db.query(models.Merchant).count())
        print("Preserved Merchant Users:", db.query(models.MerchantUser).count())

    except Exception as e:
        db.rollback()
        print(f"\nERROR during deletion: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    backup_and_clean_all_shifts()
