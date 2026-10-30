import hmac
import hashlib
import secrets
import json
import base64
import time
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

try:
    from config import settings
except ImportError:
    from backend.config import settings

import models

TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 ngày hiệu lực


def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng PBKDF2-HMAC-SHA256 với Salt ngẫu nhiên 16 bytes"""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác minh mật khẩu:
    - Hỗ trợ định dạng PBKDF2 salt$key_hex
    - Tương thích ngược với mật khẩu demo mặc định 'hashed_pw_123'
    """
    if not hashed_password or not plain_password:
        return False

    # Tương thích ngược với các tài khoản seed mặc định
    if hashed_password == "hashed_pw_123":
        return plain_password in ["123456", "hashed_pw_123", "password", "admin123", "reconhub"]

    if "$" in hashed_password:
        try:
            salt, key_hex = hashed_password.split("$", 1)
            key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
            return secrets.compare_digest(key.hex(), key_hex)
        except Exception:
            return False

    return secrets.compare_digest(plain_password, hashed_password)


def create_access_token(payload: Dict[str, Any]) -> str:
    """Sinh chuỗi Token xác thực có chữ ký HMAC-SHA256"""
    data = dict(payload)
    data["exp"] = int(time.time()) + TOKEN_EXPIRY_SECONDS
    data_json = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    data_b64 = base64.urlsafe_b64encode(data_json).decode("utf-8").rstrip("=")
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        data_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{data_b64}.{signature}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Giải mã và kiểm tra tính toàn vẹn chữ ký HMAC của Token"""
    if not token or "." not in token:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        data_b64, signature = parts
        expected_sig = hmac.new(
            settings.WEBHOOK_SECRET.encode("utf-8"),
            data_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            return None

        # Khôi phục padding base64
        pad = len(data_b64) % 4
        if pad:
            data_b64 += "=" * (4 - pad)

        data_json = base64.urlsafe_b64decode(data_b64.encode("utf-8"))
        payload = json.loads(data_json.decode("utf-8"))

        if payload.get("exp", 0) < int(time.time()):
            return None  # Hết hạn
        return payload
    except Exception:
        return None


def get_user_merchant_info(db: Session, user: models.User) -> Tuple[Optional[models.Merchant], str]:
    """Tìm cửa hàng và vai trò chính của User"""
    merchant_user = db.query(models.MerchantUser).filter(
        models.MerchantUser.user_id == user.id,
        models.MerchantUser.is_active == True
    ).first()

    if not merchant_user:
        # Fallback cửa hàng đầu tiên
        first_merchant = db.query(models.Merchant).order_by(models.Merchant.id.asc()).first()
        return first_merchant, "OWNER"

    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_user.merchant_id).first()
    return merchant, merchant_user.role


def authenticate_user(db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
    """Xác thực tài khoản và trả về gói thông tin phiên đăng nhập"""
    clean_email = (email or "").strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    merchant, role = get_user_merchant_info(db, user)
    m_id = merchant.id if merchant else 1
    m_name = merchant.name if merchant else "Cửa hàng ReconHub"

    payload = {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": role,
        "merchant_id": m_id
    }
    token = create_access_token(payload)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role,
            "merchant_id": m_id,
            "merchant_name": m_name
        }
    }


def register_new_merchant_account(
    db: Session,
    full_name: str,
    email: str,
    password: str,
    store_name: str,
    bank_bin: str = "970422",
    account_no: str = "0888999777"
) -> Dict[str, Any]:
    """Đăng ký Cửa hàng mới và Tài khoản Chủ sở hữu (Owner)"""
    clean_email = email.strip().lower()
    existing_user = db.query(models.User).filter(models.User.email == clean_email).first()
    if existing_user:
        raise ValueError("Email này đã được sử dụng. Vui lòng chọn email khác hoặc đăng nhập.")

    # 1. Tạo Merchant mới
    slug_code = f"MC_{secrets.token_hex(4).upper()}"
    webhook_secret = f"RECON_SEC_{secrets.token_hex(12)}"
    new_merchant = models.Merchant(
        merchant_code=slug_code,
        name=store_name.strip(),
        bank_bin=bank_bin.strip() or "970422",
        account_no=account_no.strip() or "0888999777",
        webhook_secret=webhook_secret,
        created_at=datetime.utcnow()
    )
    db.add(new_merchant)
    db.flush()

    # 2. Tạo User mới
    hashed_pw = hash_password(password)
    new_user = models.User(
        full_name=full_name.strip(),
        email=clean_email,
        password_hash=hashed_pw,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.flush()

    # 3. Gán quyền OWNER cho Merchant này
    merchant_user = models.MerchantUser(
        user_id=new_user.id,
        merchant_id=new_merchant.id,
        role="OWNER",
        is_active=True
    )
    db.add(merchant_user)
    db.commit()
    db.refresh(new_user)
    db.refresh(new_merchant)

    payload = {
        "user_id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": "OWNER",
        "merchant_id": new_merchant.id
    }
    token = create_access_token(payload)

    return {
        "token": token,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": "OWNER",
            "merchant_id": new_merchant.id,
            "merchant_name": new_merchant.name
        }
    }
