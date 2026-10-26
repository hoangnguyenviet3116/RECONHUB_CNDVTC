# -*- coding: utf-8 -*-
with open('backend/routers/dashboard.py', 'r', encoding='utf-8') as f:
    c = f.read()

target1 = """@router.get("/summary")
def get_dashboard_summary(
    shift_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    all_shifts = db.query(models.Shift).order_by(models.Shift.id.asc()).all()"""

replacement1 = """@router.get("/summary")
def get_dashboard_summary(
    shift_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    from services.shift_service import auto_close_expired_shifts
    auto_close_expired_shifts(db)
    all_shifts = db.query(models.Shift).order_by(models.Shift.id.asc()).all()"""

assert target1 in c, "target1 not found in dashboard.py"
c = c.replace(target1, replacement1, 1)

target2 = """    available_shifts = [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "target_revenue": float(s.target_revenue)
        }
        for s in all_shifts
    ]"""

replacement2 = """    available_shifts = [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "target_revenue": float(s.target_revenue),
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "closed_at": s.closed_at.isoformat() if s.closed_at else None
        }
        for s in all_shifts
    ]"""

assert target2 in c, "target2 not found in dashboard.py"
c = c.replace(target2, replacement2, 1)

with open('backend/routers/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated backend/routers/dashboard.py successfully")
