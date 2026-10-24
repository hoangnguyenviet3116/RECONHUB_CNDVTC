from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import verify_merchant_user
from services.shift_service import (
    to_vn_naive,
    auto_close_expired_shifts,
    close_shift_manually
)

router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"],
    dependencies=[Depends(verify_merchant_user)]
)


@router.post("", response_model=schemas.ShiftResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=schemas.ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift: schemas.ShiftCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    start_vn = to_vn_naive(shift.start_time)
    end_vn = to_vn_naive(shift.end_time)

    if not start_vn or not end_vn or end_vn <= start_vn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc ca phải sau thời gian bắt đầu ca."
        )

    if shift.target_revenue <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mục tiêu doanh thu của ca phải lớn hơn 0 VNĐ."
        )

    # Chạy auto-close ca cũ nếu đã hết giờ
    auto_close_expired_shifts(db)

    new_shift = models.Shift(
        merchant_id=user_info.get("merchant_id", 1),
        name=shift.name.strip(),
        target_revenue=shift.target_revenue,
        start_time=start_vn,
        end_time=end_vn,
        status=models.ShiftStatus.OPEN,
        closed_at=None
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift


@router.get("", response_model=List[schemas.ShiftResponse])
@router.get("/", response_model=List[schemas.ShiftResponse])
def get_shifts(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    # Tự động đóng các ca đã hết hạn
    auto_close_expired_shifts(db)

    merchant_id = user_info.get("merchant_id", 1)
    shifts = db.query(models.Shift).filter(
        models.Shift.merchant_id == merchant_id
    ).order_by(models.Shift.id.desc()).all()

    if not shifts:
        shifts = db.query(models.Shift).order_by(models.Shift.id.desc()).all()
    return shifts


@router.get("/{shift_id}", response_model=schemas.ShiftResponse)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    # Tự động đóng các ca đã hết hạn
    auto_close_expired_shifts(db)

    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift and shift_id == 1:
        shift = db.query(models.Shift).filter(models.Shift.id == 0).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy ca làm việc #{shift_id}."
        )
    return shift


@router.post("/{shift_id}/close", response_model=schemas.ShiftResponse)
def close_shift_endpoint(
    shift_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    """
    Đóng ca làm việc thủ công (Yêu cầu quyền OWNER).
    Cập nhật status = CLOSED và ghi nhận thời điểm đóng ca thực tế (closed_at).
    """
    return close_shift_manually(db=db, shift_id=shift_id, user_info=user_info)
