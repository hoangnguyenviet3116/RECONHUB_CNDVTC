from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
import models
from services.auth_service import (
    authenticate_user,
    register_new_merchant_account,
    decode_access_token,
    get_user_merchant_info
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    demo_role: Optional[str] = None


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    store_name: str
    bank_bin: Optional[str] = "970422"
    account_no: Optional[str] = "0888999777"


@router.post("/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập hệ thống:
    - Cách 1: Đăng nhập chuẩn bằng Email + Mật khẩu
    - Cách 2: Đăng nhập nhanh 1-Click bằng demo_role ('OWNER', 'REVIEWER', 'CASHIER')
    """
    # 1. Hỗ trợ Đăng nhập nhanh (Demo 1-Click)
    if payload.demo_role:
        role_target = payload.demo_role.strip().upper()
        role_map = {
            "OWNER": "owner@reconhub.vn",
            "REVIEWER": "reviewer@reconhub.vn",
            "CASHIER": "cashier@reconhub.vn"
        }
        email = role_map.get(role_target)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vai trò demo '{payload.demo_role}' không hợp lệ."
            )
        auth_data = authenticate_user(db, email, "123456")
        if not auth_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy tài khoản demo cho vai trò {role_target}."
            )
        return {
            "success": True,
            "message": "Đăng nhập nhanh demo thành công",
            "token": auth_data["token"],
            "user": auth_data["user"]
        }

    # 2. Đăng nhập chuẩn
    if not payload.email or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp đầy đủ email và mật khẩu."
        )

    auth_data = authenticate_user(db, payload.email, payload.password)
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác. Mật khẩu mặc định là '123456'."
        )

    return {
        "success": True,
        "message": "Đăng nhập thành công",
        "token": auth_data["token"],
        "user": auth_data["user"]
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Đăng ký Cửa hàng mới và Tài khoản Chủ cửa hàng (OWNER)"""
    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu phải chứa ít nhất 6 ký tự."
        )

    try:
        auth_data = register_new_merchant_account(
            db=db,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            store_name=payload.store_name,
            bank_bin=payload.bank_bin or "970422",
            account_no=payload.account_no or "0888999777"
        )
        return {
            "success": True,
            "message": "Đăng ký cửa hàng và tài khoản thành công!",
            "token": auth_data["token"],
            "user": auth_data["user"]
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi đăng ký: {str(exc)}"
        )


@router.get("/me")
def get_current_user_profile(
    authorization: Optional[str] = Header(None),
    x_demo_role: Optional[str] = Header(None, alias="X-Demo-Role"),
    x_user_id: Optional[int] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Lấy thông tin tài khoản đang đăng nhập qua Token hoặc Session Header"""
    user_id = None
    role = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("user_id")
            role = payload.get("role")

    if not user_id:
        if x_user_id:
            user_id = x_user_id
        elif x_demo_role:
            role_map = {"CASHIER": 1, "REVIEWER": 2, "OWNER": 3}
            user_id = role_map.get(x_demo_role.upper(), 3)
        else:
            user_id = 3  # Mặc định Owner

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
        )

    merchant, user_role = get_user_merchant_info(db, user)
    final_role = role or x_demo_role or user_role

    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": final_role,
            "merchant_id": merchant.id if merchant else 1,
            "merchant_name": merchant.name if merchant else "VietQR ReconHub Store"
        }
    }


@router.get("/demo-accounts")
def get_demo_accounts():
    """Danh sách tài khoản Demo để đăng nhập nhanh 1-Click trên giao diện"""
    return [
        {
            "role": "OWNER",
            "title": "Chủ Cửa Hàng",
            "name": "Lê Hồng Hạnh",
            "email": "owner@reconhub.vn",
            "password": "password: 123456",
            "icon": "crown",
            "badge": "Toàn quyền quản trị",
            "description": "Quản lý doanh thu, xem dashboard, duyệt ca và hỏi trợ lý AI Hubbie"
        },
        {
            "role": "REVIEWER",
            "title": "Kế Toán Đối Soát",
            "name": "Trần Thu Thảo",
            "email": "reviewer@reconhub.vn",
            "password": "password: 123456",
            "icon": "scale",
            "badge": "Đối soát & Duyệt",
            "description": "Rà soát giao dịch ngân hàng, xử lý lệch tiền, duyệt WebAuthn"
        },
        {
            "role": "CASHIER",
            "title": "Thu Ngân Bán Hàng",
            "name": "Nguyễn Việt Hoàng",
            "email": "cashier@reconhub.vn",
            "password": "password: 123456",
            "icon": "computer-desktop",
            "badge": "Quầy POS",
            "description": "Mở ca bán hàng, tạo đơn hàng POS và hiển thị mã VietQR động"
        }
    ]
