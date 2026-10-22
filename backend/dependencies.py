from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
import models
from database import get_db

def verify_merchant_user(
    merchant_id: int = Header(..., description="ID của cửa hàng"),
    user_id: int = Header(..., description="ID của người dùng"),
    db: Session = Depends(get_db)
):
    if not merchant_id or not user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Thiếu thông tin merchant_id hoặc user_id")
    
    # Nhóm 1: Kiểm tra thực tế trong CSDL
    user_access = db.query(models.MerchantUser).filter(
        models.MerchantUser.merchant_id == merchant_id,
        models.MerchantUser.user_id == user_id
    ).first()
    
    if not user_access:
        raise HTTPException(status_code=403, detail="Forbidden: Người dùng không thuộc cửa hàng này hoặc không có quyền truy cập")
    
    return {
        "merchant_id": merchant_id, 
        "user_id": user_id, 
        "role": user_access.role
    }