# -*- coding: utf-8 -*-
"""
Dịch vụ Quản lý Ca làm việc (Shift Service) - VietQR ReconHub
Xử lý múi giờ Asia/Ho_Chi_Minh, kiểm tra thời gian thực tế,
tự động đóng ca khi hết giờ và đóng ca thủ công an toàn.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import models
from services.merkle_tree import generate_shift_merkle_audit

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_current_vn_time() -> datetime:
    """Trả về thời gian hiện tại theo múi giờ Việt Nam (UTC+7) dạng timezone-aware"""
    return datetime.now(VN_TZ)


def get_current_vn_naive() -> datetime:
    """Trả về thời gian hiện tại theo múi giờ Việt Nam dạng naive để so sánh nhất quán với SQL Server DATETIME2"""
    return datetime.now(VN_TZ).replace(tzinfo=None)


def to_vn_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Chuyển đổi datetime sang naive datetime theo múi giờ Asia/Ho_Chi_Minh"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(VN_TZ).replace(tzinfo=None)
    return dt


def auto_close_expired_shifts(db: Session) -> List[models.Shift]:
    """
    Tự động tìm kiếm và đóng các ca làm việc đã quá giờ kết thúc (end_time <= now_vn)
    mà trạng thái vẫn đang là OPEN.
    Ghi nhận trạng thái CLOSED và thời điểm closed_at = now_vn.
    """
    now_vn = get_current_vn_naive()
    expired_shifts = db.query(models.Shift).filter(
        models.Shift.status == models.ShiftStatus.OPEN,
        models.Shift.end_time <= now_vn
    ).all()

    if not expired_shifts:
        return []

    for s in expired_shifts:
        s.status = models.ShiftStatus.CLOSED
        if not s.closed_at:
            s.closed_at = now_vn

    try:
        db.commit()
        for s in expired_shifts:
            db.refresh(s)
            try:
                generate_shift_merkle_audit(db=db, shift=s, closed_by_user_id=None)
            except Exception as me:
                print(f"Warning: Failed to generate Merkle audit for auto-closed shift #{s.id}: {me}")
    except Exception as e:
        db.rollback()
        raise e

    return expired_shifts


def validate_shift_for_order(db: Session, shift_id: int) -> models.Shift:
    """
    Kiểm tra tính hợp lệ của ca làm việc khi tiếp nhận đơn hàng hoặc phát hành QR.
    Đảm bảo:
    1. Ca tồn tại.
    2. Tự động đóng nếu đã hết giờ (end_time <= now_vn).
    3. Từ chối nếu ca đã CLOSED, DRAFT, CANCELLED.
    4. Từ chối nếu ca chưa bắt đầu (start_time > now_vn).
    5. Từ chối nếu ca đã quá thời gian kết thúc.
    Trả về đối tượng Shift hợp lệ hoặc raise HTTPException.
    """
    # Chạy lazy auto-close trước
    auto_close_expired_shifts(db)

    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ca làm việc #{shift_id} không tồn tại trong hệ thống."
        )

    now_vn = get_current_vn_naive()

    # Kiểm tra nếu ca đã hết giờ mà chưa được đóng
    if shift.end_time <= now_vn:
        if shift.status == models.ShiftStatus.OPEN:
            shift.status = models.ShiftStatus.CLOSED
            shift.closed_at = now_vn
            db.commit()
            db.refresh(shift)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ca làm việc '{shift.name}' đã hết thời gian hoạt động (kết thúc lúc {shift.end_time.strftime('%H:%M %d/%m/%Y')}). Không thể tạo đơn hàng mới."
        )

    if shift.status == models.ShiftStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ca làm việc '{shift.name}' đã đóng (CLOSED). Vui lòng mở ca mới để tiếp tục tạo đơn hàng."
        )

    if shift.status != models.ShiftStatus.OPEN:
        status_label = shift.status.value if hasattr(shift.status, "value") else str(shift.status)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ca làm việc '{shift.name}' đang ở trạng thái {status_label}, không thể nhận đơn hàng."
        )

    if shift.start_time > now_vn:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ca làm việc '{shift.name}' chưa đến thời gian bắt đầu (bắt đầu lúc {shift.start_time.strftime('%H:%M %d/%m/%Y')})."
        )

    return shift


def close_shift_manually(db: Session, shift_id: int, user_info: dict) -> models.Shift:
    """
    Đóng ca làm việc thủ công bởi người dùng có thẩm quyền (OWNER).
    """
    role = str(user_info.get("role", "")).upper()
    if role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Chủ cửa hàng (OWNER) mới có quyền đóng ca làm việc."
        )

    # Chạy lazy auto-close trước
    auto_close_expired_shifts(db)

    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy ca làm việc #{shift_id}."
        )

    if shift.status == models.ShiftStatus.CLOSED:
        closed_time_str = shift.closed_at.strftime('%H:%M %d/%m/%Y') if shift.closed_at else ""
        time_info = f" lúc {closed_time_str}" if closed_time_str else ""
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ca làm việc '{shift.name}' đã được đóng trước đó{time_info}, không thể đóng lại."
        )

    if shift.status == models.ShiftStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ca làm việc '{shift.name}' đã bị hủy bỏ."
        )

    now_vn = get_current_vn_naive()
    shift.status = models.ShiftStatus.CLOSED
    shift.closed_at = now_vn

    try:
        db.commit()
        db.refresh(shift)
        # Sinh chứng chỉ kiểm toán Merkle Tree bất biến chốt ca (Blockchain & RegTech Pillar)
        closer_id = user_info.get("id") or user_info.get("user_id")
        generate_shift_merkle_audit(db=db, shift=shift, closed_by_user_id=closer_id)
    except Exception as e:
        db.rollback()
        raise e

    return shift
