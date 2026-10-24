from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
from services.event_broadcaster import broadcaster

router = APIRouter(
    prefix="/events",
    tags=["Real-time Events (SSE)"]
)

@router.get("/stream")
async def event_stream(request: Request):
    """
    Kênh Server-Sent Events (SSE) thời gian thực truyền dữ liệu giao dịch xuống POS và Dashboard.
    Thay thế hoàn toàn cơ chế Polling 2s.
    """
    queue = broadcaster.subscribe()

    async def sse_generator():
        # Gửi sự kiện ban đầu để xác nhận kết nối thành công
        init_payload = {
            "event": "connected",
            "data": {"status": "ok", "message": "VietQR ReconHub SSE Stream Connected"}
        }
        yield f"event: connected\ndata: {json.dumps(init_payload)}\n\n"

        try:
            while True:
                # Nếu client đóng kết nối trình duyệt
                if await request.is_disconnected():
                    break

                try:
                    # Chờ sự kiện mới hoặc timeout 15s để gửi keep-alive ping
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    # Ping giữ kết nối không bị ngắt bởi proxy/firewall
                    yield ": ping keep-alive\n\n"
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
