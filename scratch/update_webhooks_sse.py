with open("backend/routers/webhooks.py", "r", encoding="utf-8") as f:
    code = f.read()

code_norm = code.replace("\r\n", "\n")

target_import = """from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
import models
from database import get_db
from services.hmac_security import verify_hmac_signature
from services.reconciliation_engine import process_automatic_reconciliation"""

replacement_import = """from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from typing import Optional
from datetime import datetime
import models
from database import get_db
from services.hmac_security import verify_hmac_signature
from services.reconciliation_engine import process_automatic_reconciliation
from services.event_broadcaster import broadcaster"""

assert target_import in code_norm, "target_import not found in webhooks.py"
code_norm = code_norm.replace(target_import, replacement_import)

target_endpoint = """@router.post("/bank-transfer", status_code=200)
async def receive_bank_transfer(
    request: Request,
    x_hub_signature: str = Header(None, description="Chữ ký HMAC-SHA256 từ Mock Bank"),
    db: Session = Depends(get_db)
):
    payload_bytes = await request.body()

    if not verify_hmac_signature(payload_bytes, x_hub_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chữ ký HMAC-SHA256 không hợp lệ hoặc giả mạo!"
        )"""

replacement_endpoint = """@router.post("/bank-transfer", status_code=200)
async def receive_bank_transfer(
    request: Request,
    x_hub_signature: str = Header(None, description="Chữ ký HMAC-SHA256 từ Ngân hàng / Cổng Open Banking"),
    x_hub_timestamp: Optional[str] = Header(None, description="Timestamp gửi bản tin chống Replay Attack"),
    db: Session = Depends(get_db)
):
    payload_bytes = await request.body()

    is_valid, err_msg = verify_hmac_signature(payload_bytes, x_hub_signature, x_hub_timestamp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err_msg
        )"""

assert target_endpoint in code_norm, "target_endpoint not found in webhooks.py"
code_norm = code_norm.replace(target_endpoint, replacement_endpoint)

target_end_fn = """    process_automatic_reconciliation(db, new_tx)
    db.refresh(new_tx)

    return {"""

replacement_end_fn = """    process_automatic_reconciliation(db, new_tx)
    db.refresh(new_tx)

    # Đẩy sự kiện SSE thời gian thực xuống quầy POS và Dashboard lập tức (< 100ms)
    broadcaster.broadcast_sync("payment_received", {
        "bank_transaction_id": new_tx.id,
        "reference_code": new_tx.reference_code,
        "amount": float(new_tx.amount),
        "allocated_amount": float(new_tx.allocated_amount),
        "unallocated_amount": float(new_tx.unallocated_amount),
        "transfer_content": new_tx.transfer_content,
        "match_status": new_tx.match_status.value if hasattr(new_tx.match_status, "value") else str(new_tx.match_status),
        "timestamp": datetime.utcnow().isoformat()
    })

    # Tìm các hóa đơn chịu ảnh hưởng bởi giao dịch này để cập nhật trạng thái đơn
    affected_allocs = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.bank_transaction_id == new_tx.id
    ).all()
    for alloc in affected_allocs:
        ord_obj = db.query(models.Order).filter(models.Order.id == alloc.order_id).first()
        if ord_obj:
            from routers.orders import enrich_order
            enriched = enrich_order(db, ord_obj)
            broadcaster.broadcast_sync("order_updated", enriched)

    return {"""

assert target_end_fn in code_norm, "target_end_fn not found in webhooks.py"
code_norm = code_norm.replace(target_end_fn, replacement_end_fn)

if "\r\n" in code:
    code_norm = code_norm.replace("\n", "\r\n")

with open("backend/routers/webhooks.py", "w", encoding="utf-8") as f:
    f.write(code_norm)

print("SUCCESS: backend/routers/webhooks.py updated with anti-replay & SSE broadcast")
