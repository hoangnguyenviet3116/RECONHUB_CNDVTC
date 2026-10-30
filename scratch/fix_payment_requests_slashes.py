# -*- coding: utf-8 -*-
with open("backend/routers/payment_requests.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '@router.get("/", response_model=List[schemas.PaymentRequestResponse])',
    '@router.get("", response_model=List[schemas.PaymentRequestResponse])\n@router.get("/", response_model=List[schemas.PaymentRequestResponse])'
)

c = c.replace(
    '@router.post("/", response_model=schemas.PaymentRequestResponse, status_code=status.HTTP_201_CREATED)',
    '@router.post("", response_model=schemas.PaymentRequestResponse, status_code=status.HTTP_201_CREATED)\n@router.post("/", response_model=schemas.PaymentRequestResponse, status_code=status.HTTP_201_CREATED)'
)

with open("backend/routers/payment_requests.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/routers/payment_requests.py")

with open("backend/routers/decisions.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '@router.get("/")',
    '@router.get("")\n@router.get("/")'
)

c = c.replace(
    '@router.post("/")',
    '@router.post("")\n@router.post("/")'
)

with open("backend/routers/decisions.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/routers/decisions.py")
