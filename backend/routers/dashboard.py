from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
import models
from database import get_db
from dependencies import verify_merchant_user
from services.hash_chain_ledger import compute_record_hash, GENESIS_HASH

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard & Ledger Verification"],
    dependencies=[Depends(verify_merchant_user)]
)

_SIMULATED_TAMPER_ACTIVE = False


@router.post("/simulate-tamper")
def toggle_simulate_tamper(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    global _SIMULATED_TAMPER_ACTIVE
    _SIMULATED_TAMPER_ACTIVE = not _SIMULATED_TAMPER_ACTIVE
    return verify_ledger_hash_chain(db=db, user_info=user_info)


@router.get("/verify-chain")
def verify_ledger_hash_chain(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    allocations = db.query(models.PaymentAllocation).order_by(models.PaymentAllocation.id.asc()).all()

    if not allocations:
        return {
            "status": "success",
            "is_valid": True,
            "valid": True,
            "ledger_integrity_valid": True,
            "message": "Sổ cái chưa có bản ghi nào.",
            "total_records": 0,
            "corrupted_record_id": None,
            "tampered_block_id": None,
            "entries": [],
            "allocations": [],
            "chain_details": []
        }

    expected_prev_hash = GENESIS_HASH
    chain_details = []
    is_chain_valid = True
    corrupted_id = None
    status_msg = "Sổ cái hoàn toàn hợp lệ và toàn vẹn tuyệt đối."

    for idx, alloc in enumerate(allocations):
        tx = db.query(models.BankTransaction).filter(models.BankTransaction.id == alloc.bank_transaction_id).first()
        order = db.query(models.Order).filter(models.Order.id == alloc.order_id).first()
        entry_type_str = alloc.entry_type.value if hasattr(alloc.entry_type, "value") else str(alloc.entry_type)

        amt_to_check = Decimal(str(alloc.allocated_amount))
        if _SIMULATED_TAMPER_ACTIVE and idx == 0:
            amt_to_check = amt_to_check + Decimal("1000000.00")

        recalculated_hash = compute_record_hash(
            prev_hash=alloc.prev_hash,
            allocation_id=alloc.id,
            bank_tx_id=alloc.bank_transaction_id,
            payment_req_id=alloc.payment_request_id,
            order_id=alloc.order_id,
            entry_type=entry_type_str,
            allocated_amount=amt_to_check,
            reversal_of_id=alloc.reversal_of_id,
            created_at=alloc.created_at
        )

        row_valid = (alloc.prev_hash == expected_prev_hash) and (alloc.record_hash == recalculated_hash)
        if not row_valid and is_chain_valid:
            is_chain_valid = False
            corrupted_id = alloc.id
            status_msg = f"PHÁT HIỆN CHỈNH SỬA TRÁI PHÉP tại bút toán ID={alloc.id}! Mã băm không khớp."

        chain_details.append({
            "id": alloc.id,
            "order_id": alloc.order_id,
            "order_code": order.order_code if order else f"ORD#{alloc.order_id}",
            "bank_transaction_id": alloc.bank_transaction_id,
            "reference_code": tx.reference_code if tx else f"TX#{alloc.bank_transaction_id}",
            "payment_request_id": alloc.payment_request_id,
            "entry_type": entry_type_str,
            "allocated_amount": float(amt_to_check),
            "reversal_of_id": alloc.reversal_of_id,
            "allocation_mode": alloc.allocation_mode.value if hasattr(alloc.allocation_mode, "value") else str(alloc.allocation_mode),
            "prev_hash": alloc.prev_hash,
            "record_hash": alloc.record_hash,
            "recalculated_hash": recalculated_hash,
            "is_valid": row_valid,
            "chain_status": ("VALID_GENESIS" if idx == 0 else "VALID_LINK") if row_valid else "TAMPERED_BROKEN_LINK",
            "created_at": alloc.created_at
        })
        expected_prev_hash = alloc.record_hash

    return {
        "status": "success" if is_chain_valid else "corrupted",
        "is_valid": is_chain_valid,
        "valid": is_chain_valid,
        "ledger_integrity_valid": is_chain_valid,
        "message": status_msg,
        "total_records": len(allocations),
        "corrupted_record_id": corrupted_id,
        "tampered_block_id": corrupted_id,
        "entries": chain_details,
        "allocations": chain_details,
        "chain_details": chain_details
    }


@router.get("/summary")
def get_dashboard_summary(
    shift_id: Optional[str] = "1",
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    open_shift = db.query(models.Shift).filter(
        models.Shift.status == models.ShiftStatus.OPEN
    ).order_by(models.Shift.id.asc()).first()

    if not open_shift:
        open_shift = db.query(models.Shift).order_by(models.Shift.id.asc()).first()

    if not open_shift:
        raise HTTPException(status_code=404, detail="Chưa có ca làm việc nào trong hệ thống.")

    if shift_id and str(shift_id).upper() != "ALL" and str(shift_id).isdigit():
        s_id = int(shift_id)
        valid_orders = db.query(models.Order).filter(
            models.Order.shift_id == s_id,
            models.Order.order_status.in_([models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW])
        ).all()
        if not valid_orders and s_id in [0, 1]:
            valid_orders = db.query(models.Order).filter(
                models.Order.order_status.in_([models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW])
            ).all()
    else:
        valid_orders = db.query(models.Order).filter(
            models.Order.order_status.in_([models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW])
        ).all()

    valid_order_ids = [o.id for o in valid_orders]
    valid_order_total = sum((Decimal(str(o.total_amount)) for o in valid_orders), Decimal("0.00"))

    if valid_order_ids:
        active_qrs = db.query(models.PaymentRequest).filter(
            models.PaymentRequest.order_id.in_(valid_order_ids),
            models.PaymentRequest.status.in_([models.PaymentRequestStatus.ACTIVE, models.PaymentRequestStatus.FULFILLED])
        ).all()
        allocations = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.order_id.in_(valid_order_ids)
        ).all()
    else:
        active_qrs = []
        allocations = []

    active_qr_request_total = sum((Decimal(str(q.expected_amount)) for q in active_qrs), Decimal("0.00"))
    allocated_payment_total = sum((Decimal(str(a.allocated_amount)) for a in allocations), Decimal("0.00"))

    all_bank_txs = db.query(models.BankTransaction).order_by(models.BankTransaction.id.desc()).all()
    unallocated_txs = [
        tx for tx in all_bank_txs
        if tx.match_status in [models.MatchStatus.UNMATCHED, models.MatchStatus.PARTIALLY_ALLOCATED]
    ]

    unallocated_bank_tx_total = sum((Decimal(str(tx.unallocated_amount)) for tx in unallocated_txs), Decimal("0.00"))
    target_rev = Decimal(str(open_shift.target_revenue))

    chain_check = verify_ledger_hash_chain(db=db, user_info=user_info)

    bank_tx_list = [
        {
            "id": tx.id,
            "merchant_id": tx.merchant_id,
            "reference_code": tx.reference_code,
            "amount": float(tx.amount),
            "allocated_amount": float(tx.allocated_amount),
            "unallocated_amount": float(tx.unallocated_amount),
            "transfer_content": tx.transfer_content,
            "sender_account": tx.sender_account,
            "match_status": tx.match_status.value if hasattr(tx.match_status, "value") else str(tx.match_status),
            "created_at": tx.created_at
        }
        for tx in all_bank_txs
    ]

    decisions_rows = db.query(models.Decision).order_by(models.Decision.id.desc()).all()
    decisions_list = []
    for d in decisions_rows:
        ord_obj = db.query(models.Order).filter(models.Order.id == d.order_id).first() if d.order_id else None
        tx_obj = db.query(models.BankTransaction).filter(models.BankTransaction.id == d.bank_transaction_id).first() if d.bank_transaction_id else None
        decisions_list.append({
            "id": d.id,
            "order_id": d.order_id,
            "order_code": ord_obj.order_code if ord_obj else f"ORD#{d.order_id}",
            "bank_transaction_id": d.bank_transaction_id,
            "reference_code": tx_obj.reference_code if tx_obj else f"TX#{d.bank_transaction_id}",
            "reviewer_id": d.reviewer_id,
            "decision_type": d.decision_type.value if hasattr(d.decision_type, "value") else str(d.decision_type),
            "reason": d.reason,
            "biometric_verified": d.biometric_verified,
            "review_date": d.review_date
        })

    return {
        "shift_id": open_shift.id,
        "shift_name": open_shift.name,
        "target_revenue": float(target_rev),
        "valid_order_total": float(valid_order_total),
        "active_qr_request_total": float(active_qr_request_total),
        "allocated_payment_total": float(allocated_payment_total),
        "unissued_qr_amount": float(valid_order_total - active_qr_request_total),
        "pending_qr_collection": float(active_qr_request_total - allocated_payment_total),
        "remaining_receivable": float(valid_order_total - allocated_payment_total),
        "unallocated_bank_tx_total": float(unallocated_bank_tx_total),
        "total_bank_received": float(allocated_payment_total + unallocated_bank_tx_total),
        "ledger_integrity_valid": chain_check["is_valid"],
        "total_ledger_records": chain_check["total_records"],
        "ledger_entries": chain_check["chain_details"],
        "payment_allocations": chain_check["chain_details"],
        "chain_details": chain_check["chain_details"],
        "bank_transactions": bank_tx_list,
        "recent_bank_transactions": bank_tx_list,
        "decisions": decisions_list,
        "recent_decisions": decisions_list
    }