from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import verify_merchant_user
from routers.dashboard import get_dashboard_summary

router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"],
    dependencies=[Depends(verify_merchant_user)]
)


@router.post("/", response_model=schemas.ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift: schemas.ShiftCreate,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    if shift.merchant_id != user_info["merchant_id"]:
        raise HTTPException(status_code=403, detail="Không được phép mở ca cho cửa hàng khác.")

    if shift.end_time <= shift.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc ca phải sau thời gian bắt đầu ca."
        )

    new_shift = models.Shift(
        merchant_id=shift.merchant_id,
        name=shift.name,
        target_revenue=shift.target_revenue,
        start_time=shift.start_time,
        end_time=shift.end_time,
        status=models.ShiftStatus.OPEN
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift


@router.get("/", response_model=List[schemas.ShiftResponse])
def get_shifts(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    query = db.query(models.Shift).filter(models.Shift.merchant_id == user_info["merchant_id"])
    return query.order_by(models.Shift.id.desc()).all()


@router.get("/{shift_id}", response_model=schemas.ShiftResponse)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    shift = db.query(models.Shift).filter(
        models.Shift.id == shift_id,
        models.Shift.merchant_id == user_info["merchant_id"]
    ).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ca làm việc hoặc bạn không có quyền truy cập."
        )
    return shift


@router.get("/{shift_id}/finance-summary")
def get_shift_finance_summary(
    shift_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    return get_dashboard_summary(shift_id=shift_id, db=db, user_info=user_info)