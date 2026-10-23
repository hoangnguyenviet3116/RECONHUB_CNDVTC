from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import models
from services.hash_chain_ledger import add_ledger_entry
from services.vietqr_service import generate_vietqr_url


def process_automatic_reconciliation(db: Session, bank_tx: models.BankTransaction):
    matched_order = None
    content_upper = (bank_tx.transfer_content or "").upper()
    for word in content_upper.replace(",", " ").replace(".", " ").split():
        if word.startswith("ORD"):
            matched_order = db.query(models.Order).filter(
                models.Order.order_code == word
            ).with_for_update().first()
            if matched_order:
                break

    if not matched_order:
        return

    # Nhóm 3: Chặn phân bổ vào đơn đã HỦY hoặc không hợp lệ
    if matched_order.order_status not in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]:
        return

    # Nhóm 3: Chặn phân bổ vào đơn đã thanh toán ĐỦ
    if matched_order.payment_status == models.PaymentStatus.PAID:
        return

    active_qr = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == matched_order.id,
        models.PaymentRequest.status == models.PaymentRequestStatus.ACTIVE
    ).first()

    # Nếu đơn hàng hợp lệ chưa có QR ACTIVE thì tự động tạo QR ACTIVE để ghi nhận vào sổ cái
    if not active_qr:
        active_qr = models.PaymentRequest(
            order_id=matched_order.id,
            request_code=f"REQ_{matched_order.order_code}_{uuid.uuid4().hex[:4].upper()}",
            expected_amount=matched_order.total_amount,
            qr_url=generate_vietqr_url("970422", "0888999777", matched_order.total_amount, matched_order.order_code),
            status=models.PaymentRequestStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db.add(active_qr)
        db.flush()

    allocations = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id == matched_order.id
    ).all()

    already_allocated = sum((Decimal(str(pa.allocated_amount)) for pa in allocations), Decimal("0.00"))
    order_total = Decimal(str(matched_order.total_amount))
    order_remaining = order_total - already_allocated

    if order_remaining <= Decimal("0.00"):
        return

    unallocated_tx = Decimal(str(bank_tx.unallocated_amount))
    alloc_amount = min(unallocated_tx, order_remaining)

    current_allocated_tx = Decimal(str(bank_tx.allocated_amount or "0.00"))
    bank_tx.allocated_amount = current_allocated_tx + alloc_amount
    bank_tx.unallocated_amount = unallocated_tx - alloc_amount

    if bank_tx.unallocated_amount == Decimal("0.00"):
        bank_tx.match_status = models.MatchStatus.FULLY_ALLOCATED
    else:
        bank_tx.match_status = models.MatchStatus.PARTIALLY_ALLOCATED

    new_total_allocated = already_allocated + alloc_amount
    if new_total_allocated >= order_total:
        matched_order.payment_status = models.PaymentStatus.PAID
        active_qr.status = models.PaymentRequestStatus.FULFILLED
    else:
        matched_order.payment_status = models.PaymentStatus.PARTIALLY_PAID

    db.commit()

    add_ledger_entry(
        db=db,
        bank_transaction_id=bank_tx.id,
        payment_request_id=active_qr.id,
        order_id=matched_order.id,
        entry_type=models.EntryType.ALLOCATION,
        allocated_amount=alloc_amount,
        reversal_of_id=None,
        allocation_mode=models.AllocationMode.AUTO
    )