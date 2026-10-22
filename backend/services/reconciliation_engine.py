from sqlalchemy.orm import Session
from decimal import Decimal
import models
from services.hash_chain_ledger import add_ledger_entry

def process_automatic_reconciliation(db: Session, bank_tx: models.BankTransaction):
    matched_order = None
    # Tìm mã đơn ORDxxxx trong nội dung chuyển khoản
    for word in bank_tx.transfer_content.split():
        if word.startswith("ORD"):
            matched_order = db.query(models.Order).filter(
                models.Order.order_code == word
            ).with_for_update().first()
            break

    if not matched_order:
        return

    # Nhóm 3: Bỏ qua đơn bị HỦY hoặc đơn không hợp lệ
    if matched_order.order_status not in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]:
        return

    # Nhóm 3: Bỏ qua đơn đã thanh toán ĐỦ
    if matched_order.payment_status == models.PaymentStatus.PAID:
        return

    # Chỉ khớp với QR đang ACTIVE
    active_qr = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == matched_order.id,
        models.PaymentRequest.status == models.PaymentRequestStatus.ACTIVE
    ).first()

    if not active_qr:
        return

    # Nhóm 3: Tính tổng số tiền ĐÃ PHÂN BỔ trước đó (gồm cả +ALLOCATION và -REVERSAL)
    allocations = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id == matched_order.id
    ).all()

    already_allocated = Decimal("0.00")
    for pa in allocations:
        already_allocated += Decimal(str(pa.allocated_amount))

    # Nhóm 3: Số tiền còn phải thu của đơn hàng
    order_total = Decimal(str(matched_order.total_amount))
    order_remaining = order_total - already_allocated

    if order_remaining <= Decimal("0.00"):
        return

    unallocated_tx = Decimal(str(bank_tx.unallocated_amount))
    
    # Số tiền phân bổ = min(tiền ngân hàng còn lại, tiền đơn hàng còn thiếu)
    alloc_amount = min(unallocated_tx, order_remaining)

    # Cập nhật số dư ngân hàng
    current_allocated_tx = Decimal(str(bank_tx.allocated_amount or "0.00"))
    bank_tx.allocated_amount = current_allocated_tx + alloc_amount
    bank_tx.unallocated_amount = unallocated_tx - alloc_amount
    
    if bank_tx.unallocated_amount == Decimal("0.00"):
        bank_tx.match_status = models.MatchStatus.FULLY_ALLOCATED
    else:
        bank_tx.match_status = models.MatchStatus.PARTIALLY_ALLOCATED

    # Cập nhật trạng thái đơn hàng & QR
    new_total_allocated = already_allocated + alloc_amount
    if new_total_allocated >= order_total:
        matched_order.payment_status = models.PaymentStatus.PAID
        active_qr.status = models.PaymentRequestStatus.FULFILLED
    else:
        matched_order.payment_status = models.PaymentStatus.PARTIALLY_PAID

    db.commit()

    # Ghi vào sổ cái Append-Only
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