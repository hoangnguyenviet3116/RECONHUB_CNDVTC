from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
import uuid
import models, schemas
from database import get_db
from dependencies import verify_merchant_user
from services.vietqr_service import generate_vietqr_url

router = APIRouter(
    prefix="/payment-requests",
    tags=["Payment Requests"],
    dependencies=[Depends(verify_merchant_user)]
)


@router.get("/", response_model=List[schemas.PaymentRequestResponse])
def get_payment_requests(
    order_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    query = db.query(models.PaymentRequest)
    if order_id is not None:
        query = query.filter(models.PaymentRequest.order_id == order_id)
    qrs = query.order_by(models.PaymentRequest.id.desc()).all()
    results = []
    for q in qrs:
        ord_obj = db.query(models.Order).filter(models.Order.id == q.order_id).first()
        ord_code = ord_obj.order_code if ord_obj else f"ORD{q.order_id}"
        results.append({
            "id": q.id,
            "order_id": q.order_id,
            "order_code": ord_code,
            "request_code": q.request_code,
            "expected_amount": q.expected_amount,
            "qr_url": q.qr_url,
            "transfer_content": f"TT {ord_code}",
            "status": q.status,
            "expires_at": q.expires_at,
            "created_at": q.created_at
        })
    return results


@router.post("/", response_model=schemas.PaymentRequestResponse, status_code=status.HTTP_201_CREATED)
def create_payment_request(
    req: schemas.PaymentRequestCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    order = db.query(models.Order).filter(models.Order.id == req.order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Đơn hàng không tồn tại."
        )

    if order.shift_id:
        from services.shift_service import get_current_vn_naive, auto_close_expired_shifts
        auto_close_expired_shifts(db)
        shift = db.query(models.Shift).filter(models.Shift.id == order.shift_id).first()
        if shift:
            now_vn = get_current_vn_naive()
            if shift.status == models.ShiftStatus.CLOSED or (shift.end_time and shift.end_time <= now_vn):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ca làm việc của đơn hàng {order.order_code} đã đóng hoặc hết hạn, không thể phát hành mã QR mới."
                )

    if order.order_status not in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn hàng không hợp lệ để phát hành QR."
        )

    if order.payment_status == models.PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn hàng này đã được thanh toán đầy đủ."
        )

    allocations = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id == order.id
    ).all()
    already_allocated = sum((Decimal(str(pa.allocated_amount)) for pa in allocations), Decimal("0.00"))
    expected_amt = Decimal(str(order.total_amount)) - already_allocated

    if expected_amt <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn hàng không còn số tiền phải thu."
        )

    active_qrs = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == order.id,
        models.PaymentRequest.status == models.PaymentRequestStatus.ACTIVE
    ).all()
    for active_qr in active_qrs:
        active_qr.status = models.PaymentRequestStatus.REVOKED
    db.flush()

    merchant = db.query(models.Merchant).order_by(models.Merchant.id.asc()).first()
    bank_bin = merchant.bank_bin if merchant else "970422"
    account_no = merchant.account_no if merchant else "0888999777"

    request_code = f"REQ_{order.order_code}_{uuid.uuid4().hex[:4].upper()}"
    qr_link = generate_vietqr_url(bank_bin, account_no, expected_amt, order.order_code)

    new_qr = models.PaymentRequest(
        order_id=order.id,
        request_code=request_code,
        expected_amount=expected_amt,
        qr_url=qr_link,
        status=models.PaymentRequestStatus.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.add(new_qr)
    db.commit()
    db.refresh(new_qr)

    return {
        "id": new_qr.id,
        "order_id": new_qr.order_id,
        "order_code": order.order_code,
        "request_code": new_qr.request_code,
        "expected_amount": new_qr.expected_amount,
        "qr_url": new_qr.qr_url,
        "transfer_content": f"TT {order.order_code}",
        "status": new_qr.status,
        "expires_at": new_qr.expires_at,
        "created_at": new_qr.created_at
    }