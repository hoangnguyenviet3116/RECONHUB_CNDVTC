import os
from pathlib import Path
from dotenv import load_dotenv

# Tìm và nạp file .env ở cả thư mục hiện tại lẫn thư mục gốc dự án
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()


class Settings:
    # Chuỗi kết nối Database SQL Server trên máy PHUONGANH\SQLEXPRESS
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mssql+pyodbc://localhost\\SQLEXPRESS/VietQR_ReconHub?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes"
    )

    # Khóa bí mật dùng cho xác minh chữ ký HMAC-SHA256
    WEBHOOK_SECRET = os.getenv(
        "WEBHOOK_SECRET",
        "RECONHUB_HMAC_SECRET_2026"
    )


settings = Settings()