# -*- coding: utf-8 -*-
with open("backend/models.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add zoneinfo import and vn_now
old_import = """from datetime import datetime
from database import Base"""

new_import = """from datetime import datetime
from zoneinfo import ZoneInfo
from database import Base

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

def vn_now():
    return datetime.now(VN_TZ).replace(tzinfo=None)"""

assert old_import in c, "old_import not found"
c = c.replace(old_import, new_import, 1)

# Replace default=datetime.utcnow with default=vn_now
c = c.replace("default=datetime.utcnow", "default=vn_now")

with open("backend/models.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/models.py successfully")
