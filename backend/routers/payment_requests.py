from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
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


@router.post("/", response_model=schemas.PaymentRequestResponse, status_code=status.HTTP_201_CREATED)
def create_payment_request(
    req: schemas.PaymentRequestCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    order = db.query(models.Order).join(models.Shift).filter(
        models.Order.id == req.order_id,
        models.Shift.merchant_id == user_info["merchant_id"]
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Đơn hàng không tồn tại hoặc bạn không có quyền truy cập."
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

    shift = db.query(models.Shift).filter(models.Shift.id == order.shift_id).first()
    merchant = db.query(models.Merchant).filter(models.Merchant.id == shift.merchant_id).first()

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
    return new_qr