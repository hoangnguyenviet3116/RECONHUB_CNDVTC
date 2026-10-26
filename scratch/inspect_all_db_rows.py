import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, "backend")
import models
from database import SessionLocal

db = SessionLocal()

print("=== USERS ===")
for u in db.query(models.User).all():
    print(f"ID={u.id}, name='{u.full_name}', email='{u.email}'")

print("\n=== MERCHANTS ===")
for m in db.query(models.Merchant).all():
    print(f"ID={m.id}, code='{m.merchant_code}', name='{m.name}'")

print("\n=== SHIFTS ===")
for s in db.query(models.Shift).all():
    print(f"ID={s.id}, name='{s.name}', status='{s.status}', target={s.target_revenue}, start={s.start_time}, end={s.end_time}")

print("\n=== ORDERS ===")
for o in db.query(models.Order).all():
    print(f"ID={o.id}, code='{o.order_code}', total={o.total_amount}, status='{o.order_status}', payment='{o.payment_status}', shift_id={o.shift_id}")

print("\n=== PAYMENT REQUESTS ===")
for pr in db.query(models.PaymentRequest).all():
    print(f"ID={pr.id}, order_id={pr.order_id}, code='{pr.request_code}', expected={pr.expected_amount}, status='{pr.status}'")

print("\n=== BANK TRANSACTIONS ===")
for bt in db.query(models.BankTransaction).all():
    print(f"ID={bt.id}, ref='{bt.reference_code}', amount={bt.amount}, allocated={bt.allocated_amount}, match='{bt.match_status}', content='{bt.transfer_content}'")

print("\n=== PAYMENT ALLOCATIONS ===")
for pa in db.query(models.PaymentAllocation).all():
    print(f"ID={pa.id}, tx_id={pa.bank_transaction_id}, order_id={pa.order_id}, amount={pa.allocated_amount}, type='{pa.entry_type}'")

print("\n=== DECISIONS ===")
for d in db.query(models.Decision).all():
    print(f"ID={d.id}, order_id={d.order_id}, type='{d.decision_type}', reason='{d.reason}'")

db.close()
