from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
from dependencies import verify_merchant_user
from services.chatbot_service import ask_assistant, build_store_context

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot AI Copilot"]
)


class ChatbotMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = []


@router.post("/ask")
def chat_with_assistant(
    req: ChatbotMessageRequest,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    """
    Tiếp nhận câu hỏi từ người dùng (Thu ngân / Chủ quán), kết hợp dữ liệu tài chính thời gian thực
    và gọi mô hình AI Ollama llama3.2 để sinh câu trả lời chính xác, thông minh.
    """
    prompt = (req.message or "").strip()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung câu hỏi không được để trống."
        )

    res = ask_assistant(db=db, user_message=prompt, history=req.history)
    return {
        "status": "success",
        "conversation_id": req.conversation_id,
        "reply": res["reply"],
        "source": res["source"],
        "model": res["model"],
        "stats": res["stats"],
        "chart_data": res.get("chart_data"),
        "suggested_actions": res.get("suggested_actions", []),
        "timestamp": res["timestamp"]
    }


@router.get("/snapshot")
def get_chatbot_store_snapshot(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    """Trả về số liệu tổng quan thời gian thực để hiển thị trên Thẻ trạng thái của Chatbot."""
    context = build_store_context(db)
    return {
        "status": "success",
        "stats": context["stats"],
        "unpaid_count": len(context["unpaid_orders"]),
        "unallocated_tx_count": len(context["unallocated_txs"])
    }
