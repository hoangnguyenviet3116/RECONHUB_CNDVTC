with open("backend/services/shift_service.py", "r", encoding="utf-8") as f:
    content = f.read()

import_target = "from sqlalchemy.orm import Session\nimport models"
import_replacement = "from sqlalchemy.orm import Session\nimport models\nfrom services.merkle_tree import generate_shift_merkle_audit"

if import_target in content:
    content = content.replace(import_target, import_replacement, 1)

# In auto_close_expired_shifts:
old_autoclose = """    try:
        db.commit()
        for s in expired_shifts:
            db.refresh(s)
    except Exception as e:
        db.rollback()
        raise e

    return expired_shifts"""

new_autoclose = """    try:
        db.commit()
        for s in expired_shifts:
            db.refresh(s)
            try:
                generate_shift_merkle_audit(db=db, shift=s, closed_by_user_id=None)
            except Exception as me:
                print(f"Warning: Failed to generate Merkle audit for auto-closed shift #{s.id}: {me}")
    except Exception as e:
        db.rollback()
        raise e

    return expired_shifts"""

if old_autoclose in content:
    content = content.replace(old_autoclose, new_autoclose, 1)

# In close_shift_manually:
old_manualclose = """    try:
        db.commit()
        db.refresh(shift)
    except Exception as e:
        db.rollback()
        raise e

    return shift"""

new_manualclose = """    try:
        db.commit()
        db.refresh(shift)
        # Sinh chứng chỉ kiểm toán Merkle Tree bất biến chốt ca (Blockchain & RegTech Pillar)
        closer_id = user_info.get("id") or user_info.get("user_id")
        generate_shift_merkle_audit(db=db, shift=shift, closed_by_user_id=closer_id)
    except Exception as e:
        db.rollback()
        raise e

    return shift"""

if old_manualclose in content:
    content = content.replace(old_manualclose, new_manualclose, 1)

with open("backend/services/shift_service.py", "w", encoding="utf-8") as f:
    f.write(content)
print("SUCCESS: backend/services/shift_service.py updated with shift closing Merkle Audit!")
