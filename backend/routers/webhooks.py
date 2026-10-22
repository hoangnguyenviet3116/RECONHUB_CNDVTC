from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
import models
from database import get_db
from services.hmac_security import verify_hmac_signature
from services.reconciliation_engine import process_automatic_reconciliation

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks & Reconciliation"]
)


@router.post("/bank-transfer", status_code=200)
async def receive_bank_transfer(
    request: Request,
    x_hub_signature: str = Header(..., description="Chữ ký HMAC-SHA256 từ Mock Bank"),
    db: Session = Depends(get_db)
):
    payload_bytes = await request.body()

    if not verify_hmac_signature(payload_bytes, x_hub_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chữ ký HMAC-SHA256 không hợp lệ hoặc giả mạo!"
        )

    payload = await request.json()

    merchant_id = payload.get("merchant_id", 1)
    reference_code = payload.get("reference_code")
    if not reference_code:
        raise HTTPException(status_code=400, detail="Thiếu mã tham chiếu giao dịch reference_code.")

    amount = Decimal(str(payload.get("amount", "0.00")))
    if amount <= Decimal("0.00"):
        raise HTTPException(status_code=400, detail="Số tiền giao dịch phải lớn hơn 0.")

    transfer_content = payload.get("transfer_content", "")
    sender_account = payload.get("sender_account", "")

    existing_tx = db.query(models.BankTransaction).filter(
        models.BankTransaction.reference_code == reference_code
    ).first()

    if existing_tx:
        raise HTTPException(status_code=400, detail="Mã giao dịch ngân hàng này đã được ghi nhận trước đó.")

    new_tx = models.BankTransaction(
        merchant_id=merchant_id,
        reference_code=reference_code,
        amount=amount,
        allocated_amount=Decimal("0.00"),
        unallocated_amount=amount,
        transfer_content=transfer_content,
        sender_account=sender_account,
        match_status=models.MatchStatus.UNMATCHED
    )
    try:
        db.add(new_tx)
        db.commit()
        db.refresh(new_tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Giao dịch trùng lặp đồng thời (reference_code đã tồn tại)."
        )

    process_automatic_reconciliation(db, new_tx)

    return {
        "status": "success",
        "message": "Đã tiếp nhận bản tin ngân hàng và xử lý phân bổ đối soát.",
        "transaction_id": new_tx.id,
        "match_status": new_tx.match_status
    }