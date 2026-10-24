from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db
from dependencies import verify_merchant_user
from routers import shifts, orders, payment_requests, webhooks, mock_bank, decisions, dashboard, events

import asyncio
from database import SessionLocal
from services.shift_service import auto_close_expired_shifts

app = FastAPI(
    title="VietQR ReconHub API",
    version="1.0.0",
    description="API cho hệ thống mô phỏng đối soát VietQR (Giai đoạn 1)"
)

async def background_shift_monitor():
    """Tác vụ nền tự động kiểm tra và đóng các ca làm việc đã quá giờ kết thúc mỗi 10 giây"""
    while True:
        try:
            db = SessionLocal()
            try:
                auto_close_expired_shifts(db)
            finally:
                db.close()
        except Exception:
            pass
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_shift_monitor())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(events.router)


# Các Alias Endpoint giúp tương thích 100% với mọi đường dẫn Fetch API trong frontend/js/*.js của Hoàng
@app.get("/bank-transactions", tags=["Aliases"])
def alias_get_bank_tx(db: Session = Depends(get_db)):
    return webhooks.get_webhook_bank_transactions(db=db)


@app.get("/payment-allocations", tags=["Aliases"])
def alias_get_allocations(db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return decisions.get_all_allocations(db=db, user_info=user_info)


@app.get("/ledger/verify-chain", tags=["Aliases"])
def alias_verify_chain(db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return dashboard.verify_ledger_hash_chain(db=db, user_info=user_info)


@app.post("/ledger/simulate-tamper", tags=["Aliases"])
def alias_simulate_tamper(db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return dashboard.toggle_simulate_tamper(db=db, user_info=user_info)


@app.post("/webauthn/register/options", tags=["Aliases"])
def alias_webauthn_reg_opt(db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return decisions.request_webauthn_register_options(db=db, user_info=user_info)


@app.post("/webauthn/register/verify", tags=["Aliases"])
def alias_webauthn_reg_ver(reg_data: dict, db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return decisions.verify_webauthn_register(reg_data=reg_data, db=db, user_info=user_info)


@app.post("/webauthn/authenticate/options", tags=["Aliases"])
def alias_webauthn_auth_opt(db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return decisions.request_webauthn_challenge(db=db, user_info=user_info)


@app.get("/shifts/{shift_id}/finance-summary", tags=["Aliases"])
def alias_shift_finance_summary(shift_id: str, db: Session = Depends(get_db), user_info: dict = Depends(verify_merchant_user)):
    return dashboard.get_dashboard_summary(shift_id=shift_id, db=db, user_info=user_info)


@app.get("/health", tags=["System"])
def check_health():
    return {"status": "ok", "message": "VietQR ReconHub API is running smoothly!"}

