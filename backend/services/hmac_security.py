import hmac
import hashlib
from config import settings

def generate_hmac_signature(payload_bytes: bytes) -> str:
    return hmac.new(
        settings.WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

def verify_hmac_signature(payload_bytes: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    computed_sig = generate_hmac_signature(payload_bytes)
    return hmac.compare_digest(computed_sig, signature_header)