from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from models import ShiftStatus, OrderStatus, PaymentStatus, PaymentRequestStatus

class ShiftBase(BaseModel):
    merchant_id: int
    name: str = Field(..., description="Tên ca làm việc")
    target_revenue: Decimal = Field(default=Decimal("0.00"), gt=Decimal("0.00"))
    start_time: datetime
    end_time: datetime

class ShiftCreate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int
    status: ShiftStatus

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    shift_id: int
    total_amount: Decimal = Field(..., gt=Decimal("0.00"), description="Tổng tiền đơn hàng phải lớn hơn 0")
    customer_note: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    shift_id: int
    created_by: int
    order_code: str
    total_amount: Decimal
    customer_note: Optional[str] = None
    order_status: OrderStatus
    payment_status: PaymentStatus

    class Config:
        from_attributes = True

class PaymentRequestCreate(BaseModel):
    order_id: int

class PaymentRequestResponse(BaseModel):
    id: int
    order_id: int
    request_code: str
    expected_amount: Decimal
    qr_url: str
    status: PaymentRequestStatus
    expires_at: datetime

    class Config:
        from_attributes = True