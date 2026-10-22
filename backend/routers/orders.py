from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import models, schemas
from database import get_db
from dependencies import verify_merchant_user

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(verify_merchant_user)]
)

@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order: schemas.OrderCreate, 
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    # Nhóm 2: Phải đảm bảo ca làm việc thuộc về merchant của người dùng
    shift = db.query(models.Shift).filter(
        models.Shift.id == order.shift_id,
        models.Shift.merchant_id == user_info["merchant_id"],
        models.Shift.status == models.ShiftStatus.OPEN
    ).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ca làm việc không tồn tại, đã đóng, hoặc không thuộc cửa hàng của bạn."
        )
    
    order_code = f"ORD{uuid.uuid4().hex[:6].upper()}"
    
    # Nhóm 2: Lấy created_by từ user_info thay vì hardcode 1
    new_order = models.Order(
        shift_id=order.shift_id,
        created_by=user_info["user_id"], 
        order_code=order_code,
        total_amount=order.total_amount,
        customer_note=order.customer_note,
        order_status=models.OrderStatus.CONFIRMED_ORDER,
        payment_status=models.PaymentStatus.UNPAID
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@router.get("/", response_model=List[schemas.OrderResponse])
def get_orders(
    shift_id: int = None, 
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    # Nhóm 2: JOIN với Shift để đảm bảo chỉ lấy đơn hàng của cửa hàng hiện tại
    query = db.query(models.Order).join(models.Shift).filter(
        models.Shift.merchant_id == user_info["merchant_id"]
    )
    if shift_id:
        query = query.filter(models.Order.shift_id == shift_id)
    return query.order_by(models.Order.id.desc()).all()

@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(
    order_id: int, 
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    # Nhóm 2: JOIN với Shift để kiểm tra quyền truy cập
    order = db.query(models.Order).join(models.Shift).filter(
        models.Order.id == order_id,
        models.Shift.merchant_id == user_info["merchant_id"]
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn hàng hoặc bạn không có quyền truy cập."
        )
    return order