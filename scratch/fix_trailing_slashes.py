# -*- coding: utf-8 -*-
with open('backend/routers/shifts.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('@router.post("/",', '@router.post("", response_model=schemas.ShiftResponse, status_code=status.HTTP_201_CREATED)\n@router.post("/",')
c = c.replace('@router.get("/",', '@router.get("", response_model=List[schemas.ShiftResponse])\n@router.get("/",')

with open('backend/routers/shifts.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated backend/routers/shifts.py")

with open('backend/routers/orders.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('@router.post("/",', '@router.post("", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)\n@router.post("/",')
c = c.replace('@router.get("/",', '@router.get("", response_model=List[schemas.OrderResponse])\n@router.get("/",')

with open('backend/routers/orders.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated backend/routers/orders.py")
