from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import uuid
import models, schemas
from database import get_db
from dependencies import verify_merchant_user

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(verify_merchant_user)]
)


def enrich_order(db: Session, order: models.Order) -> dict:
    allocs = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id == order.id
    ).order_by(models.PaymentAllocation.id.desc()).all()
    paid = sum((Decimal(str(a.allocated_amount)) for a in allocs), Decimal("0.00"))
    total = Decimal(str(order.total_amount))
    remaining = max(Decimal("0.00"), total - paid)

    overpaid = Decimal("0.00")
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
                last_transfer_content = latest_tx.transfer_content

        tx_ids = {a.bank_transaction_id for a in positive_allocs}
        txs = db.query(models.BankTransaction).filter(models.BankTransaction.id.in_(tx_ids)).all()
        overpaid = sum((Decimal(str(t.unallocated_amount)) for t in txs), Decimal("0.00"))

    qr = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == order.id,
        models.PaymentRequest.status.in_([
            models.PaymentRequestStatus.ACTIVE,
            models.PaymentRequestStatus.FULFILLED
        ])
    ).order_by(models.PaymentRequest.id.desc()).first()

    qr_dict = None
    if qr:
        qr_dict = {
            "id": qr.id,
            "order_id": qr.order_id,
            "request_code": qr.request_code,
            "expected_amount": float(qr.expected_amount),
            "qr_url": qr.qr_url,
            "status": qr.status.value if hasattr(qr.status, "value") else str(qr.status),
            "expires_at": qr.expires_at,
            "transfer_content": f"TT {order.order_code}"
        }

    note_text = order.customer_note or ""

    return {
        "id": order.id,
        "shift_id": order.shift_id,
        "created_by": order.created_by,
        "order_code": order.order_code,
        "total_amount": total,
        "customer_note": note_text,
        "note": note_text,
        "order_status": order.order_status,
        "payment_status": order.payment_status,
        "created_at": order.created_at,
        "paid_at": last_paid_at or order.created_at,
        "last_transfer_content": last_transfer_content,
        "allocated_amount": paid,
        "paid_amount": paid,
        "net_paid_amount": paid,
        "remaining_amount": remaining,
        "overpaid_amount": overpaid,
        "qr_url": qr.qr_url if qr else None,
        "request_code": qr.request_code if qr else None,
        "qr_status": (qr.status.value if hasattr(qr.status, "value") else str(qr.status)) if qr else "UNISSUED",
        "active_qr": qr_dict,
        "qr_request": qr_dict
    }


@router.post("", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    from services.shift_service import validate_shift_for_order
    shift = validate_shift_for_order(db=db, shift_id=order.shift_id)

    custom_code = (order.order_code or "").strip().upper()
    if custom_code:
        if not custom_code.startswith("ORD"):
            custom_code = f"ORD{custom_code}"
        exists = db.query(models.Order).filter(models.Order.order_code == custom_code).first()
        if exists:
            raise HTTPException(status_code=400, detail=f"Mã hóa đơn {custom_code} đã tồn tại.")
        order_code = custom_code
    else:
        all_orders = db.query(models.Order).all()
        next_num = 1001 + len(all_orders)
        order_code = f"ORD{next_num}"
        while db.query(models.Order).filter(models.Order.order_code == order_code).first():
            next_num += 1
            order_code = f"ORD{next_num}"

    note_val = order.note if order.note is not None else order.customer_note

    new_order = models.Order(
        shift_id=shift.id,
        created_by=user_info["user_id"],
        order_code=order_code,
        total_amount=order.total_amount,
        customer_note=note_val,
        order_status=models.OrderStatus.CONFIRMED_ORDER,
        payment_status=models.PaymentStatus.UNPAID
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return enrich_order(db, new_order)


@router.get("", response_model=List[schemas.OrderResponse])
@router.get("/", response_model=List[schemas.OrderResponse])
def get_orders(
    shift_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    query = db.query(models.Order)
    if shift_id is not None:
        filtered = query.filter(models.Order.shift_id == shift_id).order_by(models.Order.id.desc()).all()
        if not filtered and shift_id in [0, 1]:
            filtered = query.order_by(models.Order.id.desc()).all()
    else:
        filtered = query.order_by(models.Order.id.desc()).all()

    if payment_status and payment_status != "ALL":
        filtered = [
            o for o in filtered
            if (o.payment_status.value if hasattr(o.payment_status, "value") else str(o.payment_status)) == payment_status
        ]

    return [enrich_order(db, o) for o in filtered]


@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn hàng."
        )
    return enrich_order(db, order)