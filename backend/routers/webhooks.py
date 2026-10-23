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


@router.get("/bank-transactions")
def get_webhook_bank_transactions(db: Session = Depends(get_db)):
    txs = db.query(models.BankTransaction).order_by(models.BankTransaction.id.desc()).all()
    return [
        {
            "id": tx.id,
            "merchant_id": tx.merchant_id,
            "reference_code": tx.reference_code,
            "amount": float(tx.amount),
            "allocated_amount": float(tx.allocated_amount),
            "unallocated_amount": float(tx.unallocated_amount),
            "transfer_content": tx.transfer_content,
            "sender_account": tx.sender_account,
            "match_status": tx.match_status.value if hasattr(tx.match_status, "value") else str(tx.match_status),
            "created_at": tx.created_at
        }
        for tx in txs
    ]


@router.post("/bank-transfer", status_code=200)
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
        )

    payload = await request.json()

    first_merchant = db.query(models.Merchant).order_by(models.Merchant.id.asc()).first()
    default_m_id = first_merchant.id if first_merchant else 0
    merchant_id = payload.get("merchant_id", default_m_id)
    if db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first() is None:
        merchant_id = default_m_id

    reference_code = payload.get("reference_code")
    if not reference_code:
        raise HTTPException(status_code=400, detail="Thiếu mã giao dịch reference_code.")

    amount = Decimal(str(payload.get("amount", "0.00")))
    if amount <= Decimal("0.00"):
        raise HTTPException(status_code=400, detail="Số tiền chuyển khoản phải lớn hơn 0.")

    transfer_content = payload.get("transfer_content", "")
    sender_account = payload.get("sender_account", "0123456789")

    existing_tx = db.query(models.BankTransaction).filter(
        models.BankTransaction.reference_code == reference_code
    ).first()

    if existing_tx:
        raise HTTPException(
            status_code=400,
            detail=f"Mã giao dịch ngân hàng {reference_code} đã được ghi nhận trước đó (Chặn trùng lặp)."
        )

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
            detail=f"Giao dịch {reference_code} bị trùng lặp đồng thời."
        )

    process_automatic_reconciliation(db, new_tx)
    db.refresh(new_tx)

    return {
        "status": "success",
        "message": "Đã tiếp nhận bản tin ngân hàng và xử lý phân bổ đối soát.",
        "transaction_id": new_tx.id,
        "reference_code": new_tx.reference_code,
        "amount": float(new_tx.amount),
        "allocated_amount": float(new_tx.allocated_amount),
        "unallocated_amount": float(new_tx.unallocated_amount),
        "match_status": new_tx.match_status.value if hasattr(new_tx.match_status, "value") else str(new_tx.match_status)
    }