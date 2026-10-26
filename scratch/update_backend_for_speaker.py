import os

# 1. Update backend/schemas.py
with open("backend/schemas.py", "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")
target_schemas = """    paid_at: Optional[datetime] = None
    last_transfer_content: Optional[str] = None
    
    class Config:"""

replacement_schemas = """    paid_at: Optional[datetime] = None
    last_transfer_content: Optional[str] = None
    last_received_amount: Optional[Decimal] = None
    
    class Config:"""

assert target_schemas in content_norm, "Target schemas not found"
content_norm = content_norm.replace(target_schemas, replacement_schemas)
if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")
with open("backend/schemas.py", "w", encoding="utf-8") as f:
    f.write(content_norm)
print("SUCCESS: backend/schemas.py updated")

# 2. Update backend/routers/orders.py
with open("backend/routers/orders.py", "r", encoding="utf-8") as f:
    orders_content = f.read()

orders_norm = orders_content.replace("\r\n", "\n")

target_orders_1 = """    overpaid = Decimal("0.00")
    last_paid_at = None
    last_transfer_content = f"TT {order.order_code}"

    positive_allocs = [a for a in allocs if Decimal(str(a.allocated_amount)) > Decimal("0.00")]
    if positive_allocs:
        latest_alloc = positive_allocs[0]
        last_paid_at = latest_alloc.created_at
        latest_tx = db.query(models.BankTransaction).filter(
            models.BankTransaction.id == latest_alloc.bank_transaction_id
        ).first()
        if latest_tx:
            if latest_tx.created_at:
                last_paid_at = latest_tx.created_at
            if latest_tx.transfer_content:
                last_transfer_content = latest_tx.transfer_content"""

replacement_orders_1 = """    overpaid = Decimal("0.00")
    last_paid_at = None
    last_transfer_content = f"TT {order.order_code}"
    last_received_amount = None

    positive_allocs = [a for a in allocs if Decimal(str(a.allocated_amount)) > Decimal("0.00")]
    if positive_allocs:
        latest_alloc = positive_allocs[0]
        last_paid_at = latest_alloc.created_at
        latest_tx = db.query(models.BankTransaction).filter(
            models.BankTransaction.id == latest_alloc.bank_transaction_id
        ).first()
        if latest_tx:
            if latest_tx.created_at:
                last_paid_at = latest_tx.created_at
            if latest_tx.transfer_content:
                last_transfer_content = latest_tx.transfer_content
            if latest_tx.amount is not None:
                last_received_amount = latest_tx.amount"""

target_orders_2 = """        "paid_at": last_paid_at or order.created_at,
        "last_transfer_content": last_transfer_content,"""

replacement_orders_2 = """        "paid_at": last_paid_at or order.created_at,
        "last_transfer_content": last_transfer_content,
        "last_received_amount": last_received_amount,"""

assert target_orders_1 in orders_norm, "Target orders 1 not found"
assert target_orders_2 in orders_norm, "Target orders 2 not found"

orders_norm = orders_norm.replace(target_orders_1, replacement_orders_1)
orders_norm = orders_norm.replace(target_orders_2, replacement_orders_2)

if "\r\n" in orders_content:
    orders_norm = orders_norm.replace("\n", "\r\n")

with open("backend/routers/orders.py", "w", encoding="utf-8") as f:
    f.write(orders_norm)
print("SUCCESS: backend/routers/orders.py updated")
