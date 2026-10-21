from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models import ShiftStatus

class ShiftBase(BaseModel):
    merchant_id: int
    shift_code: str = Field(..., description="Mã ca làm việc duy nhất")
    target_revenue: float = Field(default=0, gt=0, description="Mục tiêu doanh thu phải lớn hơn 0")

class ShiftCreate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int
    status: ShiftStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None

    # Cập nhật cú pháp cho Pydantic V2
    class Config:
        from_attributes = True