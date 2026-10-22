import hashlib
from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import models

GENESIS_HASH = "GENESIS_00000000000000000000000000000000000000000000000000000000"


def format_created_at(dt: datetime) -> str:
    if isinstance(dt, str):
        return dt[:19]
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def compute_record_hash(
    prev_hash: str,
    allocation_id: int,
    bank_tx_id: int,
    payment_req_id: int,
    order_id: int,
    entry_type: str,
    allocated_amount: Decimal,
    reversal_of_id: Optional[int],
    created_at: datetime
) -> str:
    rev_str = str(reversal_of_id) if reversal_of_id is not None else "NULL"
    dt_str = format_created_at(created_at)
    amt_dec = Decimal(str(allocated_amount))
    raw_str = (
        f"{prev_hash}|{allocation_id}|{bank_tx_id}|{payment_req_id}|"
        f"{order_id}|{entry_type}|{amt_dec:.2f}|{rev_str}|{dt_str}"
    )
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def add_ledger_entry(
    db: Session,
    bank_transaction_id: int,
    payment_request_id: int,
    order_id: int,
    entry_type: models.EntryType,
    allocated_amount: Decimal,
    reversal_of_id: Optional[int] = None,
    allocation_mode: models.AllocationMode = models.AllocationMode.AUTO
) -> models.PaymentAllocation:
    last_entry = db.query(models.PaymentAllocation).order_by(
        models.PaymentAllocation.id.desc()
    ).with_for_update().first()

    prev_hash = last_entry.record_hash if (last_entry and last_entry.record_hash) else GENESIS_HASH
    now_dt = datetime.utcnow().replace(microsecond=0)
    amt_dec = Decimal(str(allocated_amount))
    entry_type_str = entry_type.value if hasattr(entry_type, "value") else str(entry_type)

    new_alloc = models.PaymentAllocation(
        bank_transaction_id=bank_transaction_id,
        payment_request_id=payment_request_id,
        order_id=order_id,
        entry_type=entry_type,
        allocated_amount=amt_dec,
        reversal_of_id=reversal_of_id,
        allocation_mode=allocation_mode,
        created_at=now_dt,
        prev_hash=prev_hash,
        record_hash="PENDING"
    )

    db.add(new_alloc)
    db.flush()

    new_alloc.record_hash = compute_record_hash(
        prev_hash=prev_hash,
        allocation_id=new_alloc.id,
        bank_tx_id=bank_transaction_id,
        payment_req_id=payment_request_id,
        order_id=order_id,
        entry_type=entry_type_str,
        allocated_amount=amt_dec,
        reversal_of_id=reversal_of_id,
        created_at=now_dt
    )

    db.commit()
    db.refresh(new_alloc)
    return new_alloc