import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('backend')
from database import SessionLocal
import models

db = SessionLocal()
all_allocs = db.query(models.PaymentAllocation).all()
tx_to_orders = {}
for a in all_allocs:
    if a.bank_transaction_id not in tx_to_orders:
        tx_to_orders[a.bank_transaction_id] = []
    tx_to_orders[a.bank_transaction_id].append((a.order_id, a.allocated_amount))

print('=== ALL 34 BANK TRANSACTIONS ===')
for tx in db.query(models.BankTransaction).order_by(models.BankTransaction.id.asc()).all():
    linked = tx_to_orders.get(tx.id, [])
    ord_shifts = []
    for oid, amt in linked:
        o = db.query(models.Order).filter(models.Order.id == oid).first()
        if o:
            ord_shifts.append((o.id, o.order_code, f"shift_{o.shift_id}"))
    print(f'TX #{tx.id}: {tx.reference_code}, amt={tx.amount}, content="{tx.transfer_content}", linked={ord_shifts}')

print('\n=== ALL 13 DECISIONS ===')
for d in db.query(models.Decision).all():
    print(f'Dec #{d.id}: order_id={d.order_id}, tx_id={d.bank_transaction_id}, type={d.decision_type}, reason={d.reason[:30]}')

db.close()
