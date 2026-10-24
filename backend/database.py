from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    from config import settings
except ImportError:
    from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    use_setinputsizes=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# Tự động sửa các tên ca bị lỗi font 'Ca chi?u' đã lưu trước đó trong SQL Server
try:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE dbo.shifts SET name = REPLACE(name, N'Ca chi?u', N'Ca chiều') WHERE name LIKE N'%Ca chi?u%'")
        )
        conn.execute(
            text("UPDATE dbo.shifts SET name = REPLACE(name, N'Ca s?ng', N'Ca sáng') WHERE name LIKE N'%Ca s?ng%'")
        )
        conn.execute(
            text("UPDATE dbo.shifts SET name = REPLACE(name, N'Ca t?i', N'Ca tối') WHERE name LIKE N'%Ca t?i%'")
        )
except Exception:
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()