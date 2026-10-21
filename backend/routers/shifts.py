from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import verify_merchant_user

router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"],
    dependencies=[Depends(verify_merchant_user)] # P1-04: Yêu cầu phân quyền cho mọi API trong router này
)

@router.post("/", response_model=schemas.ShiftResponse, status_code=201)
def create_shift(shift: schemas.ShiftCreate, db: Session = Depends(get_db)):
    """P1-08: Mở ca làm việc mới"""
    # Kiểm tra mã ca đã tồn tại chưa
    db_shift = db.query(models.Shift).filter(models.Shift.shift_code == shift.shift_code).first()
    if db_shift:
        raise HTTPException(status_code=400, detail="Mã ca làm việc đã tồn tại")
    
    new_shift = models.Shift(
        merchant_id=shift.merchant_id,
        shift_code=shift.shift_code,
        target_revenue=shift.target_revenue,
        status=models.ShiftStatus.OPEN
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift

@router.get("/", response_model=List[schemas.ShiftResponse])
def get_shifts(db: Session = Depends(get_db)):
    """P1-07: Lấy danh sách ca làm việc"""
    shifts = db.query(models.Shift).all()
    return shifts

@router.get("/{shift_id}", response_model=schemas.ShiftResponse)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    """P1-07: Lấy thông tin chi tiết một ca làm việc"""
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
         raise HTTPException(status_code=404, detail="Không tìm thấy ca làm việc")
    return shift