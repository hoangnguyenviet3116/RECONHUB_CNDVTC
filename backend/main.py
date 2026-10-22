from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

from routers import shifts, orders, payment_requests, webhooks, mock_bank, decisions, dashboard

app = FastAPI(
    title="VietQR ReconHub API",
    version="1.0.0",
    description="API cho hệ thống mô phỏng đối soát VietQR (Giai đoạn 1)"
)

# Nhóm 1: Giới hạn CORS cụ thể cho Frontend thay vì dùng ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", 
        "http://localhost:5500", 
        "http://127.0.0.1:3000", 
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shifts.router)
app.include_router(orders.router)
app.include_router(payment_requests.router)
app.include_router(webhooks.router)
app.include_router(mock_bank.router)
app.include_router(decisions.router)
app.include_router(dashboard.router)

@app.get("/health", tags=["System"])
def check_health():
    return {"status": "ok", "message": "VietQR ReconHub API is running smoothly!"}