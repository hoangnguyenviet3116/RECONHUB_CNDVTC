from fastapi import APIRouter, HTTPException
import json
import requests
from services.hmac_security import generate_hmac_signature

router = APIRouter(
    prefix="/mock-bank",
    tags=["Mock Bank Simulator"]
)

WEBHOOK_URL = "http://127.0.0.1:8000/webhooks/bank-transfer"

@router.post("/trigger-transfer", status_code=200)
def trigger_mock_bank_transfer(payload: dict):
    payload_json = json.dumps(payload, sort_keys=True)
    payload_bytes = payload_json.encode('utf-8')

    signature = generate_hmac_signature(payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "x-hub-signature": signature
    }

    try:
        response = requests.post(WEBHOOK_URL, data=payload_bytes, headers=headers)
        return {
            "status": "triggered",
            "mock_bank_response_code": response.status_code,
            "response_data": response.json()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể kết nối đến Webhook endpoint: {str(e)}")