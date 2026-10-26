import sys, os
sys.path.insert(0, "backend")
import models
from database import SessionLocal
db = SessionLocal()
order = db.query(models.Order).filter(models.Order.id == 6).first()
if order:
    print("Order 6:", order.order_code, order.payment_status, order.created_at)
    allocs = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.order_id == 6).all()
    print("Allocs for 6:", [(a.id, a.allocated_amount, a.created_at, a.bank_transaction_id) for a in allocs])
    pr = db.query(models.PaymentRequest).filter(models.PaymentRequest.order_id == 6).all()
    print("PRs for 6:", [(p.id, p.request_code, p.status) for p in pr])
else:
    print("Order 6 not found")
db.close()
