from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import models
from database import engine
from routers import shifts

# Load biến môi trường
load_dotenv()

# Tự động tạo bảng trong DB nếu chưa có
models.Base.metadata.create_all(bind=engine)

# Khởi tạo biến app (Lỗi của bạn nằm ở việc Uvicorn không tìm thấy dòng này)
app = FastAPI(title="VietQR ReconHub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(shifts.router)

@app.get("/health", tags=["System"])
def check_health():
    return {"status": "ok", "message": "VietQR ReconHub API is running smoothly!"}