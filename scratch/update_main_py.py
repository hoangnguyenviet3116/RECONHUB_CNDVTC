# -*- coding: utf-8 -*-
with open('backend/main.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """app = FastAPI(
    title="VietQR ReconHub API",
    version="1.0.0",
    description="API cho hệ thống mô phỏng đối soát VietQR (Giai đoạn 1)"
)"""

replacement = """import asyncio
from database import SessionLocal
from services.shift_service import auto_close_expired_shifts

app = FastAPI(
    title="VietQR ReconHub API",
    version="1.0.0",
    description="API cho hệ thống mô phỏng đối soát VietQR (Giai đoạn 1)"
)

async def background_shift_monitor():
    \"\"\"Tác vụ nền tự động kiểm tra và đóng các ca làm việc đã quá giờ kết thúc mỗi 10 giây\"\"\"
    while True:
        try:
            db = SessionLocal()
            try:
                auto_close_expired_shifts(db)
            finally:
                db.close()
        except Exception:
            pass
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_shift_monitor())"""

assert target in c, "target not found in main.py"
c = c.replace(target, replacement, 1)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated backend/main.py successfully")
