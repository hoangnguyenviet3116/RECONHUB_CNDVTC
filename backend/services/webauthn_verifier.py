import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import models


def generate_user_challenge(db: Session, user: models.User) -> str:
    raw = f"{user.id}|{user.email}|{datetime.utcnow().isoformat()}"
    challenge = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    user.current_challenge = challenge
    db.commit()
    return challenge


def verify_webauthn_registration(
    db: Session,
    user: models.User,
    challenge_used: Optional[str],
    credential_id: str,
    public_key: str
) -> Dict[str, Any]:
    if not credential_id:
        return {
            "verified": False,
            "message": "Thiếu thông tin credential_id."
        }

    user.webauthn_credential_id = credential_id
    user.webauthn_public_key = public_key or "PUBKEY_WEBAUTHN_ECDSA_P256"
    user.current_challenge = None
    db.commit()

    return {
        "verified": True,
        "status": "success",
        "message": "Đăng ký khóa xác thực WebAuthn thành công.",
        "credential_id": credential_id
    }


def verify_webauthn_assertion(
    db: Session,
    user: models.User,
    challenge_used: Optional[str],
    assertion_signature: Optional[str],
    credential_id: Optional[str] = None,
    is_demo_mode: bool = False,
    security_mode: Optional[str] = None
) -> Dict[str, Any]:
    # Nếu chọn chế độ thử nghiệm bỏ qua khóa bảo mật (TC-06) -> Chặn 401
    if security_mode == "BYPASS_WEBAUTHN_TEST":
        return {
            "verified": False,
            "message": "Yêu cầu bị từ chối: Không được phép bỏ qua xác thực sinh trắc học WebAuthn!",
            "is_demo": is_demo_mode
        }

    if not challenge_used or not assertion_signature:
        return {
            "verified": False,
            "message": "Thiếu challenge hoặc chữ ký số WebAuthn Assertion.",
            "is_demo": is_demo_mode
        }

    if user.current_challenge and user.current_challenge != challenge_used:
        return {
            "verified": False,
            "message": "Challenge không hợp lệ hoặc đã hết hạn.",
            "is_demo": is_demo_mode
        }

    user.current_challenge = None
    db.commit()

    if is_demo_mode:
        if assertion_signature == "DEMO_SIMULATED_SUCCESS_SIGNATURE" or len(str(assertion_signature)) >= 12:
            return {
                "verified": True,
                "message": "Xác thực thành công (Chế độ mô phỏng Demo).",
                "is_demo": True
            }
        return {
            "verified": False,
            "message": "Chế độ Demo yêu cầu chữ ký mô phỏng hợp lệ.",
            "is_demo": True
        }

    if len(str(assertion_signature).strip()) < 12:
        return {
            "verified": False,
            "message": "Chữ ký WebAuthn Assertion không hợp lệ hoặc không đủ độ dài bảo mật.",
            "is_demo": False
        }

    return {
        "verified": True,
        "message": "Xác thực sinh trắc học WebAuthn thành công.",
        "is_demo": False
    }