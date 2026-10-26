# -*- coding: utf-8 -*-
with open('backend/routers/payment_requests.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Đơn hàng không tồn tại."
        )"""

replacement = """    if not order:
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
                )"""

assert target in c, "target not found in payment_requests.py"
c = c.replace(target, replacement, 1)

with open('backend/routers/payment_requests.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated backend/routers/payment_requests.py successfully")
