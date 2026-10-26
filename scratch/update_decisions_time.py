# -*- coding: utf-8 -*-
with open("backend/routers/decisions.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("expires_at=datetime.utcnow()", "expires_at=models.vn_now()")
c = c.replace("and qr.expires_at > datetime.utcnow()", "and qr.expires_at > models.vn_now()")

with open("backend/routers/decisions.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/routers/decisions.py successfully")
