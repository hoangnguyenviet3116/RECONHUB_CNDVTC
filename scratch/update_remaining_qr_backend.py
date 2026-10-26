# 1. Update backend/services/reconciliation_engine.py
with open("backend/services/reconciliation_engine.py", "r", encoding="utf-8") as f:
    rec_code = f.read()

rec_norm = rec_code.replace("\r\n", "\n")

target_rec = """    new_total_allocated = already_allocated + alloc_amount
    if new_total_allocated >= order_total:
        matched_order.payment_status = models.PaymentStatus.PAID
        active_qr.status = models.PaymentRequestStatus.FULFILLED
    else:
        matched_order.payment_status = models.PaymentStatus.PARTIALLY_PAID

    db.commit()"""

replacement_rec = """    new_total_allocated = already_allocated + alloc_amount
    if new_total_allocated >= order_total:
        matched_order.payment_status = models.PaymentStatus.PAID
        active_qr.status = models.PaymentRequestStatus.FULFILLED
    else:
        matched_order.payment_status = models.PaymentStatus.PARTIALLY_PAID
        # Thu hồi mã QR cũ (vì số tiền cũ không còn đúng) và tự động tạo mã QR ACTIVE mới cho số tiền còn thiếu
        active_qr.status = models.PaymentRequestStatus.REVOKED
        remaining_amt = order_total - new_total_allocated
        merchant = db.query(models.Merchant).order_by(models.Merchant.id.asc()).first()
        b_bin = merchant.bank_bin if merchant else "970422"
        acc_no = merchant.account_no if merchant else "0888999777"
        new_qr = models.PaymentRequest(
            order_id=matched_order.id,
            request_code=f"REQ_{matched_order.order_code}_{uuid.uuid4().hex[:4].upper()}",
            expected_amount=remaining_amt,
            qr_url=generate_vietqr_url(b_bin, acc_no, remaining_amt, matched_order.order_code),
            status=models.PaymentRequestStatus.ACTIVE,
            expires_at=models.vn_now() + timedelta(minutes=15)
        )
        db.add(new_qr)

    db.commit()"""

assert target_rec in rec_norm, "Target rec not found"
rec_norm = rec_norm.replace(target_rec, replacement_rec)

if "\r\n" in rec_code:
    rec_norm = rec_norm.replace("\n", "\r\n")

with open("backend/services/reconciliation_engine.py", "w", encoding="utf-8") as f:
    f.write(rec_norm)
print("SUCCESS: backend/services/reconciliation_engine.py updated")


# 2. Update backend/routers/orders.py
with open("backend/routers/orders.py", "r", encoding="utf-8") as f:
    orders_code = f.read()

orders_norm = orders_code.replace("\r\n", "\n")

target_orders_import = """from dependencies import verify_merchant_user"""
replacement_orders_import = """from dependencies import verify_merchant_user
from services.vietqr_service import generate_vietqr_url"""

target_orders_qr = """    qr = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == order.id,
        models.PaymentRequest.status.in_([
            models.PaymentRequestStatus.ACTIVE,
            models.PaymentRequestStatus.FULFILLED
        ])
    ).order_by(models.PaymentRequest.id.desc()).first()"""

replacement_orders_qr = """    qr = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == order.id,
        models.PaymentRequest.status.in_([
            models.PaymentRequestStatus.ACTIVE,
            models.PaymentRequestStatus.FULFILLED
        ])
    ).order_by(models.PaymentRequest.id.desc()).first()

    # Đảm bảo mã QR ACTIVE của đơn hàng đang chuyển thiếu luôn hiển thị đúng 100% số tiền khách còn thiếu
    if qr and qr.status == models.PaymentRequestStatus.ACTIVE and remaining > Decimal("0.00"):
        if Decimal(str(qr.expected_amount)) != remaining:
            qr.expected_amount = remaining
            merchant = db.query(models.Merchant).order_by(models.Merchant.id.asc()).first()
            b_bin = merchant.bank_bin if merchant else "970422"
            acc_no = merchant.account_no if merchant else "0888999777"
            qr.qr_url = generate_vietqr_url(b_bin, acc_no, remaining, order.order_code)
            try:
                db.commit()
                db.refresh(qr)
            except Exception:
                db.rollback()"""

assert target_orders_import in orders_norm, "Target orders import not found"
assert target_orders_qr in orders_norm, "Target orders qr not found"

orders_norm = orders_norm.replace(target_orders_import, replacement_orders_import)
orders_norm = orders_norm.replace(target_orders_qr, replacement_orders_qr)

if "\r\n" in orders_code:
    orders_norm = orders_norm.replace("\n", "\r\n")

with open("backend/routers/orders.py", "w", encoding="utf-8") as f:
    f.write(orders_norm)
print("SUCCESS: backend/routers/orders.py updated")
