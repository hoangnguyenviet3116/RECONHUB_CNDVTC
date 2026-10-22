
import os
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env
load_dotenv()


class Settings:
    # Chuỗi kết nối SQL Server
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Khóa bí mật dùng cho HMAC-SHA256
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


settings = Settings()
