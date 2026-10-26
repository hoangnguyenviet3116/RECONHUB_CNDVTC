import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, "backend")
from database import engine
from sqlalchemy import text

print("=================================================================")
print("DỌN DẸP DỮ LIỆU GIAO DỊCH MẪU TRONG CƠ SỞ DỮ LIỆU SQL SERVER")
print("=================================================================")

cleanup_sql = """
SET NOCOUNT ON;
BEGIN TRANSACTION;

-- Xóa dữ liệu giao dịch mẫu theo đúng thứ tự ràng buộc khóa ngoại (Foreign Keys)
DELETE FROM dbo.decisions;
DELETE FROM dbo.payment_allocations;
DELETE FROM dbo.bank_transactions;
DELETE FROM dbo.payment_requests;
DELETE FROM dbo.orders;
DELETE FROM dbo.shifts;

-- Reset bộ đếm tự tăng IDENTITY của 6 bảng giao dịch về 0
DBCC CHECKIDENT ('dbo.decisions', RESEED, 0);
DBCC CHECKIDENT ('dbo.payment_allocations', RESEED, 0);
DBCC CHECKIDENT ('dbo.bank_transactions', RESEED, 0);
DBCC CHECKIDENT ('dbo.payment_requests', RESEED, 0);
DBCC CHECKIDENT ('dbo.orders', RESEED, 0);
DBCC CHECKIDENT ('dbo.shifts', RESEED, 0);

COMMIT TRANSACTION;
"""

batches = [b.strip() for b in cleanup_sql.split(";") if b.strip() and not b.strip().startswith("SET")]

with engine.begin() as conn:
    for stmt in batches:
        if stmt in ("BEGIN TRANSACTION", "COMMIT TRANSACTION"):
            continue
        conn.execute(text(stmt))

print(">>> [THÀNH CÔNG] Đã dọn dẹp sạch toàn bộ dữ liệu mẫu trong 6 bảng giao dịch!")
print(">>> [BẢO TỒN] Bảng merchants, users và merchant_users vẫn được giữ nguyên vẹn 100%.")
