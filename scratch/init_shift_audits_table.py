import sys
sys.path.append('backend')
from database import engine, text, Base
import models

with engine.begin() as conn:
    res = conn.execute(text("SELECT OBJECT_ID('dbo.shift_audits', 'U')")).scalar()
    print("dbo.shift_audits table exists before:", res is not None)
    if res is None:
        print("Creating dbo.shift_audits table via SQLAlchemy Base.metadata.create_all...")
        models.Base.metadata.create_all(bind=engine)
        res_after = conn.execute(text("SELECT OBJECT_ID('dbo.shift_audits', 'U')")).scalar()
        print("dbo.shift_audits table exists after:", res_after is not None)
