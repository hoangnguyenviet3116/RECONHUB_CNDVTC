import hmac
import hashlib
import time
from typing import Optional, Tuple
from config import settings

# Bộ nhớ đệm chống Replay Attack (Idempotency Cache) với TTL
_SEEN_SIGNATURES = {}  # {sig_or_key: expiry_time}

def _cleanup_seen_signatures(now_time: float):
    expired = [k for k, exp in _SEEN_SIGNATURES.items() if exp < now_time]
    for k in expired:
        _SEEN_SIGNATURES.pop(k, None)


def generate_hmac_signature(payload_bytes: bytes, timestamp: Optional[str] = None) -> str:
    """
    Sinh chữ ký HMAC-SHA256 chuẩn bảo mật ngân hàng mở:
    Nếu có timestamp, chữ ký được tính trên f"{timestamp}." + payload_bytes
    """
    data_to_sign = payload_bytes
    if timestamp:
        data_to_sign = f"{timestamp}.".encode('utf-8') + payload_bytes

    return hmac.new(
        settings.WEBHOOK_SECRET.encode('utf-8'),
        data_to_sign,
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(
    payload_bytes: bytes,
    signature_header: str,
    timestamp_header: Optional[str] = None,
    tolerance_seconds: int = 300
) -> Tuple[bool, str]:
    """
    Xác minh tính hợp lệ của chữ ký HMAC-SHA256:
    1. Kiểm tra chữ ký rỗng.
    2. Nếu có timestamp_header: Kiểm tra Tolerance Window (chống Replay Attack).
    3. Kiểm tra tính trùng lặp trong cửa sổ thời gian (Idempotency Cache).
    4. So sánh chữ ký an toàn với hmac.compare_digest.
    """
    if not signature_header:
        return False, "Thiếu chữ ký x-hub-signature."

    now_time = time.time()
    _cleanup_seen_signatures(now_time)

    # 1. Xác minh có kèm Timestamp (Chế độ chuẩn bảo mật ngân hàng mở)
    if timestamp_header:
        try:
            ts_float = float(timestamp_header)
            # Kiểm tra độ lệch thời gian (Tolerance Window)
            if abs(now_time - ts_float) > tolerance_seconds:
                return False, f"Chữ ký webhook đã hết hạn (lệch {abs(now_time - ts_float):.0f}s > {tolerance_seconds}s). Từ chối Replay Attack!"
        except ValueError:
            return False, "Header x-hub-timestamp không đúng định dạng timestamp."

        # Kiểm tra replay attack qua idempotency cache
        cache_key = f"{signature_header}:{timestamp_header}"
        if cache_key in _SEEN_SIGNATURES:
            return False, "Phát hiện tấn công phát lại (Replay Attack): Bản tin webhook này đã được gửi trước đó!"

        computed_sig = generate_hmac_signature(payload_bytes, timestamp=timestamp_header)
        if hmac.compare_digest(computed_sig, signature_header):
            _SEEN_SIGNATURES[cache_key] = now_time + tolerance_seconds
            return True, "OK"
        return False, "Chữ ký HMAC-SHA256 (kèm timestamp) không chính xác!"

    # 2. Chế độ tương thích ngược (Legacy payload-only signature)
    computed_sig = generate_hmac_signature(payload_bytes)
    if hmac.compare_digest(computed_sig, signature_header):
        return True, "OK"

    return False, "Chữ ký HMAC-SHA256 không hợp lệ hoặc bị giả mạo!"
