from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from decimal import Decimal
from models import ShiftStatus, OrderStatus, PaymentStatus, PaymentRequestStatus


class ShiftBase(BaseModel):
    merchant_id: Optional[int] = 1
    name: str = Field(..., description="Tên ca làm việc")
    target_revenue: Decimal = Field(default=Decimal("100000000.00"), gt=Decimal("0.00"))
    start_time: datetime
    end_time: datetime


class ShiftCreate(ShiftBase):
    status: Optional[ShiftStatus] = ShiftStatus.OPEN


class ShiftResponse(ShiftBase):
    id: int
    status: ShiftStatus
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    shift_id: int
    total_amount: Decimal = Field(..., gt=Decimal("0.00"), description="Tổng tiền đơn hàng phải lớn hơn 0")
    customer_note: Optional[str] = None
    note: Optional[str] = None
    order_code: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    shift_id: int
    created_by: int
    order_code: str
    total_amount: Decimal
    customer_note: Optional[str] = None
    note: Optional[str] = None
    order_status: OrderStatus
    payment_status: PaymentStatus
    created_at: Optional[datetime] = None
    allocated_amount: Optional[Decimal] = Decimal("0.00")
    paid_amount: Optional[Decimal] = Decimal("0.00")
    net_paid_amount: Optional[Decimal] = Decimal("0.00")
    remaining_amount: Optional[Decimal] = Decimal("0.00")
    overpaid_amount: Optional[Decimal] = Decimal("0.00")
    qr_url: Optional[str] = None
    request_code: Optional[str] = None
    qr_status: Optional[str] = None
    active_qr: Optional[Any] = None
    qr_request: Optional[Any] = None
    paid_at: Optional[datetime] = None
    last_transfer_content: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaymentRequestCreate(BaseModel):
    order_id: int
    expected_amount: Optional[Decimal] = None


class PaymentRequestResponse(BaseModel):
    id: int
    order_id: int
    order_code: Optional[str] = None
    request_code: str
    expected_amount: Decimal
    qr_url: str
    transfer_content: Optional[str] = None
    status: PaymentRequestStatus
    expires_at: datetime
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True