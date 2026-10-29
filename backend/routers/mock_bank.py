from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import requests
import models
from database import get_db
from services.hmac_security import generate_hmac_signature

router = APIRouter(
    prefix="/mock-bank",
    tags=["Mock Bank Simulator"]
)

WEBHOOK_URL = "http://127.0.0.1:8000/webhooks/bank-transfer"


@router.get("/transactions")
def list_mock_bank_transactions(db: Session = Depends(get_db)):
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


@router.post("/trigger-transfer", status_code=200)
def trigger_mock_bank_transfer(payload: dict, db: Session = Depends(get_db)):
    test_mode = payload.get("test_mode", "STANDARD")
    is_invalid_hmac = (
        test_mode == "INVALID_HMAC"
        or payload.get("invalid_hmac") is True
        or payload.get("tamper_signature") is True
        or payload.get("simulate_invalid_hmac") is True
    )

    first_merchant = db.query(models.Merchant).order_by(models.Merchant.id.asc()).first()
    payload["merchant_id"] = first_merchant.id if first_merchant else 0

    payload_json = json.dumps(payload, sort_keys=True)
    payload_bytes = payload_json.encode("utf-8")

    import time
    now_ts = time.time()
    if test_mode == "REPLAY_ATTACK" or payload.get("simulate_replay") is True:
        # Giả lập bản tin cũ quá hạn (600s trước > 300s tolerance)
        ts_str = str(now_ts - 600)
    else:
        ts_str = str(now_ts)

    if is_invalid_hmac:
        signature = "INVALID_TAMPERED_HMAC_SIGNATURE_0000000000000000"
    else:
        signature = generate_hmac_signature(payload_bytes, timestamp=ts_str)

    headers = {
        "Content-Type": "application/json",
        "x-hub-signature": signature,
        "x-hub-timestamp": ts_str
    }

    try:
        response = requests.post(WEBHOOK_URL, data=payload_bytes, headers=headers, timeout=5.0)
        resp_data = response.json() if response.content else {}

        # Nếu Webhook từ chối (401 sai HMAC hoặc 400 trùng mã GD), trả đúng HTTP status đó về cho Frontend hiển thị
        if response.status_code >= 400:
            detail_msg = resp_data.get("detail") or resp_data.get("message") or "Giao dịch bị từ chối."
            raise HTTPException(status_code=response.status_code, detail=detail_msg)

        return {
            "status": "triggered",
            "message": resp_data.get("message", "Đã tiếp nhận bản tin ngân hàng và xử lý phân bổ đối soát."),
            "mock_bank_response_code": response.status_code,
            "transaction_id": resp_data.get("transaction_id"),
            "reference_code": resp_data.get("reference_code"),
            "response_data": resp_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Không thể kết nối đến Webhook endpoint: {str(e)}"
        )