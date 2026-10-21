from fastapi import Header, HTTPException

async def verify_merchant_user(merchant_id: int = Header(..., description="ID của cửa hàng"), user_id: int = Header(..., description="ID của người dùng")):
    """
    Middleware/Dependency kiểm tra quyền truy cập cửa hàng.
    Trong MVP, ta giả lập lấy từ Header. Nếu trái cửa hàng sẽ trả về 403.
    """
    # TODO: Khi có DB, truy vấn bảng merchant_users để kiểm tra user_id có thuộc merchant_id không.
    # user_role = db.query(MerchantUser).filter_by(merchant_id=merchant_id, user_id=user_id).first()
    
    # Mock validation tạm thời
    if not merchant_id or not user_id:
         raise HTTPException(status_code=403, detail="Forbidden: Thiếu thông tin xác thực cửa hàng.")
    
    # Trả về thông tin giả lập để các API khác dùng
    return {"merchant_id": merchant_id, "user_id": user_id, "role": "OWNER"}