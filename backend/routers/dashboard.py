from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
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
            "ledger_integrity_valid": True,
            "message": "Sổ cái chưa có bản ghi nào.",
            "total_records": 0,
            "corrupted_record_id": None,
            "chain_details": []
        }

    expected_prev_hash = GENESIS_HASH
    chain_details = []

    for idx, alloc in enumerate(allocations):
        entry_type_str = alloc.entry_type.value if hasattr(alloc.entry_type, "value") else str(alloc.entry_type)
        recalculated_hash = compute_record_hash(
            prev_hash=alloc.prev_hash,
            allocation_id=alloc.id,
            bank_tx_id=alloc.bank_transaction_id,
            payment_req_id=alloc.payment_request_id,
            order_id=alloc.order_id,
            entry_type=entry_type_str,
            allocated_amount=Decimal(str(alloc.allocated_amount)),
            reversal_of_id=alloc.reversal_of_id,
            created_at=alloc.created_at
        )

        if alloc.prev_hash != expected_prev_hash:
            return {
                "status": "corrupted",
                "is_valid": False,
                "ledger_integrity_valid": False,
                "message": f"Mắt xích chuỗi băm bị đứt gãy tại bản ghi ID={alloc.id}. prev_hash không khớp!",
                "total_records": len(allocations),
                "corrupted_record_id": alloc.id,
                "chain_details": chain_details
            }

        if alloc.record_hash != recalculated_hash:
            return {
                "status": "corrupted",
                "is_valid": False,
                "ledger_integrity_valid": False,
                "message": f"Dữ liệu bản ghi ID={alloc.id} đã bị chỉnh sửa trái phép! Hash không khớp.",
                "total_records": len(allocations),
                "corrupted_record_id": alloc.id,
                "chain_details": chain_details
            }

        chain_details.append({
            "id": alloc.id,
            "order_id": alloc.order_id,
            "bank_transaction_id": alloc.bank_transaction_id,
            "payment_request_id": alloc.payment_request_id,
            "entry_type": entry_type_str,
            "allocated_amount": Decimal(str(alloc.allocated_amount)),
            "reversal_of_id": alloc.reversal_of_id,
            "prev_hash": alloc.prev_hash,
            "record_hash": alloc.record_hash,
            "chain_status": "VALID_GENESIS" if idx == 0 else "VALID_LINK"
        })
        expected_prev_hash = alloc.record_hash

    return {
        "status": "success",
        "is_valid": True,
        "ledger_integrity_valid": True,
        "message": "Sổ cái hoàn toàn hợp lệ và toàn vẹn tuyệt đối.",
        "total_records": len(allocations),
        "corrupted_record_id": None,
        "chain_details": chain_details
    }


@router.get("/summary")
def get_dashboard_summary(
    shift_id: int = 1,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    shift = db.query(models.Shift).filter(
        models.Shift.id == shift_id,
        models.Shift.merchant_id == user_info["merchant_id"]
    ).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ca làm việc hoặc ca không thuộc cửa hàng của bạn."
        )

    valid_orders = db.query(models.Order).filter(
        models.Order.shift_id == shift_id,
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

    unallocated_txs = db.query(models.BankTransaction).filter(
        models.BankTransaction.merchant_id == user_info["merchant_id"],
        models.BankTransaction.match_status.in_([models.MatchStatus.UNMATCHED, models.MatchStatus.PARTIALLY_ALLOCATED])
    ).all()

    unallocated_bank_tx_total = sum((Decimal(str(tx.unallocated_amount)) for tx in unallocated_txs), Decimal("0.00"))

    chain_check = verify_ledger_hash_chain(db=db, user_info=user_info)

    return {
        "shift_id": shift.id,
        "shift_name": shift.name,
        "merchant_id": user_info["merchant_id"],
        "target_revenue": Decimal(str(shift.target_revenue)),
        "valid_order_total": valid_order_total,
        "active_qr_request_total": active_qr_request_total,
        "allocated_payment_total": allocated_payment_total,
        "unissued_qr_amount": valid_order_total - active_qr_request_total,
        "pending_qr_collection": active_qr_request_total - allocated_payment_total,
        "remaining_receivable": valid_order_total - allocated_payment_total,
        "unallocated_bank_tx_total": unallocated_bank_tx_total,
        "total_bank_received": allocated_payment_total + unallocated_bank_tx_total,
        "ledger_integrity_valid": chain_check["is_valid"]
    }