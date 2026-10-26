import sys
sys.path.insert(0, "backend")
import models
from database import SessionLocal

db = SessionLocal()
print("Merchants:", db.query(models.Merchant).count())
print("Users:", db.query(models.User).count())
print("Shifts:", db.query(models.Shift).count())
print("Orders:", db.query(models.Order).count())
print("Payment Requests:", db.query(models.PaymentRequest).count())
print("Bank Transactions:", db.query(models.BankTransaction).count())
print("Allocations:", db.query(models.PaymentAllocation).count())
print("Decisions:", db.query(models.Decision).count())
db.close()
