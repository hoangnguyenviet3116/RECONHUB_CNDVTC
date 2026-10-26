# -*- coding: utf-8 -*-
with open("backend/services/hash_chain_ledger.py", "r", encoding="utf-8") as f:
    c = f.read()

target = "    now_dt = datetime.utcnow().replace(microsecond=0)"
replacement = """    from zoneinfo import ZoneInfo
    vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now_dt = datetime.now(vn_tz).replace(tzinfo=None, microsecond=0)"""

assert target in c, "target not found"
c = c.replace(target, replacement, 1)

with open("backend/services/hash_chain_ledger.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/services/hash_chain_ledger.py successfully")
