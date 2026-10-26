# -*- coding: utf-8 -*-
with open("backend/services/reconciliation_engine.py", "r", encoding="utf-8") as f:
    c = f.read()

target = "expires_at=datetime.utcnow() + timedelta(minutes=15)"
replacement = "expires_at=models.vn_now() + timedelta(minutes=15)"

assert target in c, "target not found"
c = c.replace(target, replacement, 1)

with open("backend/services/reconciliation_engine.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/services/reconciliation_engine.py successfully")
