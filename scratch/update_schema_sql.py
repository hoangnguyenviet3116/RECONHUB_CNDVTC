with open("database/schema_sqlserver.sql", "r", encoding="utf-8") as f:
    sql = f.read()

ddl_shift_audits = """
-- BẢNG 10: shift_audits (Lưu chứng chỉ kiểm toán Merkle Tree bất biến khi chốt ca - RegTech Pillar)
CREATE TABLE dbo.shift_audits (
    id INT IDENTITY(1,1) PRIMARY KEY,
    shift_id INT NOT NULL,
    merchant_id INT NOT NULL,
    closed_by INT NULL,
    total_orders INT NOT NULL DEFAULT 0,
    total_revenue DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_allocations INT NOT NULL DEFAULT 0,
    merkle_root VARCHAR(64) NOT NULL,
    first_record_hash VARCHAR(64) NULL,
    last_record_hash VARCHAR(64) NULL,
    audit_signature NVARCHAR(500) NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_shift_audits_shift UNIQUE (shift_id),
    CONSTRAINT FK_shift_audits_shifts FOREIGN KEY (shift_id) REFERENCES dbo.shifts(id),
    CONSTRAINT FK_shift_audits_merchants FOREIGN KEY (merchant_id) REFERENCES dbo.merchants(id),
    CONSTRAINT FK_shift_audits_users FOREIGN KEY (closed_by) REFERENCES dbo.users(id)
);
GO
"""

if "CREATE TABLE dbo.shift_audits" not in sql:
    sql += ddl_shift_audits
    with open("database/schema_sqlserver.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    print("SUCCESS: schema_sqlserver.sql updated with shift_audits DDL!")
else:
    print("shift_audits already in schema_sqlserver.sql")
