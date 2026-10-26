import sys
sys.path.append('backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("""
        SELECT cc.name, cc.definition 
        FROM sys.check_constraints cc
        JOIN sys.tables t ON cc.parent_object_id = t.object_id
        WHERE t.name = 'decisions'
    """)).fetchall()
    for row in res:
        print(row)
