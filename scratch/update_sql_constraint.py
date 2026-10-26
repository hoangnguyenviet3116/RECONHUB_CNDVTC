import sys
sys.path.append('backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE dbo.decisions DROP CONSTRAINT CK_decisions_type;"))
    conn.execute(text("ALTER TABLE dbo.decisions ADD CONSTRAINT CK_decisions_type CHECK (decision_type IN ('APPROVE_MANUAL_MATCH', 'REVERSE_ALLOCATION', 'REQUEST_INFO', 'REJECT_TX', 'OVERPAYMENT_RESOLUTION'));"))
    conn.commit()
    print("SUCCESS: Updated CK_decisions_type constraint in SQL Server")
