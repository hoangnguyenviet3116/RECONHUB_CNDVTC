# -*- coding: utf-8 -*-
with open('backend/routers/orders.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_block = """    shift = db.query(models.Shift).filter(models.Shift.id == order.shift_id).first()
    if not shift:
        shift = db.query(models.Shift).filter(
            models.Shift.status == models.ShiftStatus.OPEN
        ).order_by(models.Shift.id.asc()).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ca làm việc không tồn tại hoặc đã đóng."
        )"""

new_block = """    from services.shift_service import validate_shift_for_order
    shift = validate_shift_for_order(db=db, shift_id=order.shift_id)"""

assert old_block in c, "old_block not found in orders.py"
c = c.replace(old_block, new_block, 1)

with open('backend/routers/orders.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated backend/routers/orders.py successfully")
