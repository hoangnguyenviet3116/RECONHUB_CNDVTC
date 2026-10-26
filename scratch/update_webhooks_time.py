# -*- coding: utf-8 -*-
with open("backend/routers/webhooks.py", "r", encoding="utf-8") as f:
    c = f.read()

target = """    new_tx = models.BankTransaction(
        merchant_id=merchant_id,
        reference_code=reference_code,
        amount=amount,
        allocated_amount=Decimal("0.00"),
        unallocated_amount=amount,
        transfer_content=transfer_content,
        sender_account=sender_account,
        match_status=models.MatchStatus.UNMATCHED
    )"""

replacement = """    from datetime import datetime
    from zoneinfo import ZoneInfo
    vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")

    raw_time = payload.get("transfer_time") or payload.get("transaction_date")
    if raw_time:
        try:
            if isinstance(raw_time, str):
                parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    tx_time = parsed.astimezone(vn_tz).replace(tzinfo=None)
                else:
                    tx_time = parsed
            elif isinstance(raw_time, datetime):
                if raw_time.tzinfo is not None:
                    tx_time = raw_time.astimezone(vn_tz).replace(tzinfo=None)
                else:
                    tx_time = raw_time
            else:
                tx_time = datetime.now(vn_tz).replace(tzinfo=None)
        except Exception:
            tx_time = datetime.now(vn_tz).replace(tzinfo=None)
    else:
        tx_time = datetime.now(vn_tz).replace(tzinfo=None)

    new_tx = models.BankTransaction(
        merchant_id=merchant_id,
        reference_code=reference_code,
        amount=amount,
        allocated_amount=Decimal("0.00"),
        unallocated_amount=amount,
        transfer_content=transfer_content,
        sender_account=sender_account,
        match_status=models.MatchStatus.UNMATCHED,
        created_at=tx_time
    )"""

assert target in c, "target not found"
c = c.replace(target, replacement, 1)

with open("backend/routers/webhooks.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated backend/routers/webhooks.py successfully")
