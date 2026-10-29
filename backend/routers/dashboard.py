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
    date: Optional[str] = None,
    shift_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    from services.shift_service import auto_close_expired_shifts
    auto_close_expired_shifts(db)
    all_shifts = db.query(models.Shift).order_by(models.Shift.id.asc()).all()
    if not all_shifts:
        return {
            "status": "success",
            "shift_id": "ALL",
            "shift_name": "Chưa có ca làm việc",
            "target_revenue": Decimal("0.00"),
            "valid_order_total": Decimal("0.00"),
            "cancelled_order_total": Decimal("0.00"),
            "total_order_amount": Decimal("0.00"),
            "total_order_count": 0,
            "valid_order_count": 0,
            "cancelled_order_count": 0,
            "active_qr_request_total": Decimal("0.00"),
            "allocated_payment_total": Decimal("0.00"),
            "unissued_qr_amount": Decimal("0.00"),
            "pending_qr_collection": Decimal("0.00"),
            "remaining_receivable": Decimal("0.00"),
            "unallocated_bank_tx_total": Decimal("0.00"),
            "total_bank_received": Decimal("0.00"),
            "bank_transaction_count": 0,
            "allocated_order_count": 0,
            "unpaid_order_count": 0,
            "unallocated_bank_tx_count": 0,
            "ledger_integrity_valid": True,
            "orders": [],
            "available_shifts": [],
            "ledger_entries": [],
            "bank_transactions": [],
            "payment_allocations": [],
            "decisions": []
        }

    # Thu thập danh sách các ngày có ca làm việc
    available_dates_set = {s.start_time.strftime("%Y-%m-%d") for s in all_shifts if s.start_time}
    available_dates = sorted(list(available_dates_set), reverse=True)

    from datetime import datetime as dt_cls
    today_str = dt_cls.now().strftime("%Y-%m-%d")
    selected_date_str = date.strip() if (date and date.strip()) else (available_dates[0] if available_dates else today_str)

    # Lọc các ca thuộc ngày được chọn
    day_shifts = [
        s for s in all_shifts
        if s.start_time and s.start_time.strftime("%Y-%m-%d") == selected_date_str
    ]
    day_shift_ids = [s.id for s in day_shifts]

    # Tính toán mảng biến động doanh thu theo từng ca trong ngày (Shift Breakdown)
    shift_breakdown = []
    for s in day_shifts:
        s_orders = db.query(models.Order).filter(models.Order.shift_id == s.id).all()
        s_valid = [o for o in s_orders if o.order_status in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]]
        s_valid_total = sum((Decimal(str(o.total_amount)) for o in s_valid), Decimal("0.00"))
        s_valid_ids = [o.id for o in s_valid]
        s_allocs = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.order_id.in_(s_valid_ids)).all() if s_valid_ids else []
        s_allocated_total = sum((Decimal(str(a.allocated_amount)) for a in s_allocs), Decimal("0.00"))
        shift_breakdown.append({
            "shift_id": s.id,
            "shift_name": s.name,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "target_revenue": float(s.target_revenue),
            "valid_order_total": float(s_valid_total),
            "allocated_payment_total": float(s_allocated_total),
            "remaining_receivable": float(max(Decimal("0.00"), s_valid_total - s_allocated_total)),
            "order_count": len(s_valid),
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None
        })

    # Xác định ca làm việc cần đối soát:
    # 1. "ALL": Tổng hợp toàn bộ các ca trong ngày đó (Chế độ 1)
    # 2. Mã số cụ thể (VD: "1", "3"): Lấy đúng ca tương ứng (Chế độ 2)
    # 3. None/Trống: Mặc định hiển thị tổng hợp ngày (Chế độ 1)
    selected_shift = None
    is_all_shifts = False

    if shift_id and str(shift_id).strip().upper() == "ALL":
        is_all_shifts = True
        shift_id_res = "ALL"
        shift_name_res = f"Tất cả ca trong ngày ({selected_date_str})"
        target_rev = sum((Decimal(str(s.target_revenue)) for s in day_shifts), Decimal("0.00"))
        if day_shift_ids:
            orders_query = db.query(models.Order).filter(models.Order.shift_id.in_(day_shift_ids))
        else:
            orders_query = db.query(models.Order).filter(models.Order.id == -1)
    elif shift_id and str(shift_id).strip().isdigit():
        s_id = int(shift_id)
        selected_shift = db.query(models.Shift).filter(models.Shift.id == s_id).first()
        if not selected_shift:
            shift_id_res = s_id
            shift_name_res = f'Ca {s_id}'
            target_rev = Decimal('0.00')
            orders_query = db.query(models.Order).filter(models.Order.shift_id == s_id)
        else:
            shift_id_res = selected_shift.id
            shift_name_res = selected_shift.name
            target_rev = Decimal(str(selected_shift.target_revenue))
            orders_query = db.query(models.Order).filter(models.Order.shift_id == selected_shift.id)
    else:
        # Khi chỉ lọc ngày mà không chọn ca: Mặc định là tổng hợp toàn bộ ngày
        is_all_shifts = True
        shift_id_res = "ALL"
        shift_name_res = f"Tất cả ca trong ngày ({selected_date_str})"
        target_rev = sum((Decimal(str(s.target_revenue)) for s in day_shifts), Decimal("0.00"))
        if day_shift_ids:
            orders_query = db.query(models.Order).filter(models.Order.shift_id.in_(day_shift_ids))
        else:
            orders_query = db.query(models.Order).filter(models.Order.id == -1)

    all_orders_in_scope = orders_query.order_by(models.Order.id.desc()).all()

    valid_orders = [
        o for o in all_orders_in_scope
        if o.order_status in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]
    ]
    cancelled_orders = [
        o for o in all_orders_in_scope
        if o.order_status == models.OrderStatus.CANCELLED_ORDER
    ]

    valid_order_ids = [o.id for o in valid_orders]
    valid_order_total = sum((Decimal(str(o.total_amount)) for o in valid_orders), Decimal("0.00"))
    cancelled_order_total = sum((Decimal(str(o.total_amount)) for o in cancelled_orders), Decimal("0.00"))
    total_order_amount = sum((Decimal(str(o.total_amount)) for o in all_orders_in_scope), Decimal("0.00"))

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

    chain_check = verify_ledger_hash_chain(db=db, user_info=user_info)

    bank_tx_list = []
    for tx in all_bank_txs:
        decision = db.query(models.Decision).filter(
            models.Decision.bank_transaction_id == tx.id
        ).order_by(models.Decision.id.desc()).first()

        alloc = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.bank_transaction_id == tx.id,
            models.PaymentAllocation.entry_type == models.EntryType.ALLOCATION
        ).first()
        linked_order = db.query(models.Order).filter(models.Order.id == alloc.order_id).first() if alloc else None
        if not linked_order and tx.transfer_content:
            for word in (tx.transfer_content or "").upper().replace(",", " ").replace(".", " ").split():
                if word.startswith("ORD"):
                    linked_order = db.query(models.Order).filter(models.Order.order_code == word).first()
                    if linked_order:
                        break

        is_ovp = False
        if linked_order:
            order_is_paid = (linked_order.payment_status == models.PaymentStatus.PAID)
            if float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0:
                is_ovp = True
            elif order_is_paid and float(tx.unallocated_amount or 0) > 0:
                is_ovp = True
        bank_tx_list.append({
            "id": tx.id,
            "merchant_id": tx.merchant_id,
            "reference_code": tx.reference_code,
            "amount": float(tx.amount),
            "allocated_amount": float(tx.allocated_amount),
            "unallocated_amount": float(tx.unallocated_amount),
            "transfer_content": tx.transfer_content,
            "sender_account": tx.sender_account,
            "match_status": tx.match_status.value if hasattr(tx.match_status, "value") else str(tx.match_status),
            "created_at": tx.created_at,
            "order_id": linked_order.id if linked_order else None,
            "order_code": linked_order.order_code if linked_order else None,
            "order_amount": float(linked_order.total_amount) if linked_order else None,
            "is_overpayment": is_ovp,
            "is_handled": bool(decision is not None),
            "decision_type": (decision.decision_type.value if hasattr(decision.decision_type, "value") else str(decision.decision_type)) if decision else None,
            "handling_method": decision.reason if decision else None
        })

    decisions_rows = db.query(models.Decision).order_by(models.Decision.id.desc()).all()
    decisions_list = []
    for d in decisions_rows:
        ord_obj = db.query(models.Order).filter(models.Order.id == d.order_id).first() if d.order_id else None
        tx_obj = db.query(models.BankTransaction).filter(models.BankTransaction.id == d.bank_transaction_id).first() if d.bank_transaction_id else None
        reviewer_obj = db.query(models.User).filter(models.User.id == d.reviewer_id).first() if d.reviewer_id else None
        decisions_list.append({
            "id": d.id,
            "order_id": d.order_id,
            "order_code": ord_obj.order_code if ord_obj else None,
            "order_amount": float(ord_obj.total_amount) if ord_obj else None,
            "bank_transaction_id": d.bank_transaction_id,
            "reference_code": tx_obj.reference_code if tx_obj else None,
            "tx_amount": float(tx_obj.amount) if tx_obj else None,
            "allocated_amount": float(tx_obj.allocated_amount) if tx_obj else None,
            "unallocated_amount": float(tx_obj.unallocated_amount) if tx_obj else None,
            "reviewer_id": d.reviewer_id,
            "reviewer_name": reviewer_obj.full_name if reviewer_obj else f"Nhân viên #{d.reviewer_id}",
            "decision_type": d.decision_type.value if hasattr(d.decision_type, "value") else str(d.decision_type),
            "reason": d.reason,
            "biometric_verified": d.biometric_verified,
            "review_date": d.review_date.isoformat() if hasattr(d.review_date, "isoformat") else str(d.review_date)
        })

    from routers.orders import enrich_order
    formatted_orders = [enrich_order(db, o) for o in all_orders_in_scope]

    available_shifts = [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "target_revenue": float(s.target_revenue),
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "closed_at": s.closed_at.isoformat() if s.closed_at else None
        }
        for s in all_shifts
    ]

    all_order_ids_in_scope = {o.id for o in all_orders_in_scope}
    scoped_ledger_entries = (
        chain_check["chain_details"]
        if is_all_shifts
        else [entry for entry in chain_check["chain_details"] if entry["order_id"] in all_order_ids_in_scope]
    )

    return {
        "selected_date": selected_date_str,
        "available_dates": available_dates,
        "is_day_summary": is_all_shifts,
        "shift_breakdown": shift_breakdown,
        "day_shifts": [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                "target_revenue": float(s.target_revenue),
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "closed_at": s.closed_at.isoformat() if s.closed_at else None,
                "date": s.start_time.strftime("%Y-%m-%d") if s.start_time else None
            }
            for s in day_shifts
        ],
        "shift_id": shift_id_res,
        "shift_name": shift_name_res,
        "target_revenue": float(target_rev),
        "valid_order_total": float(valid_order_total),
        "cancelled_order_total": float(cancelled_order_total),
        "total_order_amount": float(total_order_amount),
        "total_order_count": len(all_orders_in_scope),
        "valid_order_count": len(valid_orders),
        "cancelled_order_count": len(cancelled_orders),
        "active_qr_request_total": float(active_qr_request_total),
        "allocated_payment_total": float(allocated_payment_total),
        "unissued_qr_amount": float(max(Decimal("0.00"), valid_order_total - active_qr_request_total)),
        "pending_qr_collection": float(max(Decimal("0.00"), active_qr_request_total - allocated_payment_total)),
        "remaining_receivable": float(max(Decimal("0.00"), valid_order_total - allocated_payment_total)),
        "unallocated_bank_tx_total": float(unallocated_bank_tx_total),
        "total_bank_received": float(allocated_payment_total + unallocated_bank_tx_total),
        "ledger_integrity_valid": chain_check["is_valid"],
        "total_ledger_records": len(scoped_ledger_entries),
        "ledger_entries": scoped_ledger_entries,
        "payment_allocations": chain_check["chain_details"],
        "chain_details": chain_check["chain_details"],
        "orders": formatted_orders,
        "available_shifts": available_shifts,
        "bank_transactions": bank_tx_list,
        "recent_bank_transactions": bank_tx_list,
        "decisions": decisions_list,
        "recent_decisions": decisions_list
    }
    
