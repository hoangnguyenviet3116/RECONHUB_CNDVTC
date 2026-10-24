import asyncio
import json
import logging
from typing import Set, Dict, Any, AsyncGenerator

logger = logging.getLogger("event_broadcaster")

class EventBroadcaster:
    """
    Quản lý luồng sự kiện thời gian thực Server-Sent Events (SSE)
    Sử dụng asyncio.Queue theo mô hình Pub/Sub cho các quầy thu ngân POS và màn hình giám sát.
    """
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        logger.info(f"SSE client connected. Total active subscribers: {len(self._subscribers)}")
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)
            logger.info(f"SSE client disconnected. Total active subscribers: {len(self._subscribers)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """
        Đẩy sự kiện tới toàn bộ client đang mở kết nối SSE.
        """
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": data.get("timestamp") or ""
        }
        raw_message = f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        dead_queues = set()
        for q in list(self._subscribers):
            try:
                # Không chặn nếu hàng đợi của client đầy (loại bỏ non-blocking)
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(raw_message)
            except Exception as e:
                logger.warning(f"Error delivering event to queue: {e}")
                dead_queues.add(q)

        for dq in dead_queues:
            self.unsubscribe(dq)

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]):
        """
        Cho phép gọi phát sự kiện từ các hàm đồng bộ (Synchronous service / route).
        """
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            # Nếu chạy ngoài event loop chính
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.broadcast(event_type, data), loop)
                else:
                    loop.run_until_complete(self.broadcast(event_type, data))
            except Exception as ex:
                logger.warning(f"Could not broadcast sync event: {ex}")


broadcaster = EventBroadcaster()
