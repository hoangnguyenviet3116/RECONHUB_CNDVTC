import sys
import re

# 1. Update backend/routers/decisions.py
with open("backend/routers/decisions.py", "r", encoding="utf-8") as f:
    dec_code = f.read()

dec_norm = dec_code.replace("\r\n", "\n")

target_get_decisions = """@router.get("/")
def get_decisions_history(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    decisions = db.query(models.Decision).order_by(models.Decision.id.desc()).all()
    results = []
    for d in decisions:
        order = db.query(models.Order).filter(models.Order.id == d.order_id).first() if d.order_id else None
        tx = db.query(models.BankTransaction).filter(models.BankTransaction.id == d.bank_transaction_id).first() if d.bank_transaction_id else None
        reviewer = db.query(models.User).filter(models.User.id == d.reviewer_id).first()
        results.append({
            "id": d.id,
            "order_id": d.order_id,
            "order_code": order.order_code if order else None,
            "bank_transaction_id": d.bank_transaction_id,
            "reference_code": tx.reference_code if tx else None,
            "reviewer_id": d.reviewer_id,
            "reviewer_name": reviewer.full_name if reviewer else f"User #{d.reviewer_id}",
            "decision_type": d.decision_type.value if hasattr(d.decision_type, "value") else str(d.decision_type),
            "reason": d.reason,
            "challenge_used": d.challenge_used,
            "assertion_signature": d.assertion_signature,
            "biometric_verified": d.biometric_verified,
            "review_date": d.review_date
        })
    return results


@router.get("/unmatched-transactions")
def get_unmatched_transactions(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    txs = db.query(models.BankTransaction).filter(
        models.BankTransaction.unallocated_amount > 0
    ).order_by(models.BankTransaction.id.desc()).all()
    return [
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
        for tx in txs
    ]"""

replacement_get_decisions = """@router.get("/")
def get_decisions_history(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    decisions = db.query(models.Decision).order_by(models.Decision.id.desc()).all()
    results = []
    for d in decisions:
        order = db.query(models.Order).filter(models.Order.id == d.order_id).first() if d.order_id else None
        tx = db.query(models.BankTransaction).filter(models.BankTransaction.id == d.bank_transaction_id).first() if d.bank_transaction_id else None
        reviewer = db.query(models.User).filter(models.User.id == d.reviewer_id).first()
        results.append({
            "id": d.id,
            "order_id": d.order_id,
            "order_code": order.order_code if order else None,
            "order_amount": float(order.total_amount) if order else None,
            "bank_transaction_id": d.bank_transaction_id,
            "reference_code": tx.reference_code if tx else None,
            "tx_amount": float(tx.amount) if tx else None,
            "allocated_amount": float(tx.allocated_amount) if tx else None,
            "unallocated_amount": float(tx.unallocated_amount) if tx else None,
            "reviewer_id": d.reviewer_id,
            "reviewer_name": reviewer.full_name if reviewer else f"User #{d.reviewer_id}",
            "decision_type": d.decision_type.value if hasattr(d.decision_type, "value") else str(d.decision_type),
            "reason": d.reason,
            "challenge_used": d.challenge_used,
            "assertion_signature": d.assertion_signature,
            "biometric_verified": d.biometric_verified,
            "review_date": d.review_date.isoformat() if hasattr(d.review_date, "isoformat") else str(d.review_date)
        })
    return results


@router.get("/unmatched-transactions")
def get_unmatched_transactions(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    txs = db.query(models.BankTransaction).filter(
        models.BankTransaction.unallocated_amount > 0
    ).order_by(models.BankTransaction.id.desc()).all()
    results = []
    for tx in txs:
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

        is_ovp = bool(linked_order and float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0)
        results.append({
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
    return results"""

assert target_get_decisions in dec_norm, "Target get decisions not found"
dec_norm = dec_norm.replace(target_get_decisions, replacement_get_decisions)

# Target for make_decision manual match check
target_manual_match = """        requested_amt = decision_data.get("amount") or decision_data.get("allocated_amount")
        alloc_amount = min(unallocated_tx, order_remaining)
        if requested_amt is not None:
            req_dec = Decimal(str(requested_amt))
            if req_dec > Decimal("0.00"):
                alloc_amount = min(alloc_amount, req_dec)"""

replacement_manual_match = """        requested_amt = decision_data.get("amount") or decision_data.get("allocated_amount")
        if requested_amt is not None:
            req_dec = Decimal(str(requested_amt))
            if req_dec <= Decimal("0.00"):
                raise HTTPException(status_code=400, detail="Số tiền phân bổ phải lớn hơn 0 VNĐ.")
            if req_dec > unallocated_tx:
                raise HTTPException(
                    status_code=400,
                    detail=f"Số tiền phân bổ ({req_dec:,.0f} đ) vượt quá số tiền chưa phân bổ của giao dịch ({unallocated_tx:,.0f} đ)."
                )
            if req_dec > order_remaining:
                raise HTTPException(
                    status_code=400,
                    detail=f"Số tiền phân bổ ({req_dec:,.0f} đ) vượt quá số tiền còn thiếu của đơn hàng ({order_remaining:,.0f} đ)."
                )
            alloc_amount = req_dec
        else:
            alloc_amount = min(unallocated_tx, order_remaining)"""

assert target_manual_match in dec_norm, "Target manual match not found"
dec_norm = dec_norm.replace(target_manual_match, replacement_manual_match)

# Add OVERPAYMENT_RESOLUTION to make_decision
target_reverse_end = """        return {
            "status": "success",
            "message": f"Đảo bút toán #{orig_alloc.id} thành công (-{orig_amount:,.0f} VNĐ).",
            "reversal_allocation_id": reversal_alloc.id,
            "decision_id": decision_rec.id
        }

    raise HTTPException(status_code=400, detail="Loại quyết định không hợp lệ.")"""

replacement_reverse_end = """        return {
            "status": "success",
            "message": f"Đảo bút toán #{orig_alloc.id} thành công (-{orig_amount:,.0f} VNĐ).",
            "reversal_allocation_id": reversal_alloc.id,
            "decision_id": decision_rec.id
        }

    elif decision_type == "OVERPAYMENT_RESOLUTION":
        if not tx_id:
            raise HTTPException(status_code=400, detail="Thiếu thông tin bank_transaction_id.")

        method_plan = (decision_data.get("reason") or decision_data.get("handling_method") or "").strip()
        if not method_plan:
            raise HTTPException(status_code=400, detail="Vui lòng nhập phương thức xử lý khoản tiền thừa.")

        tx = db.query(models.BankTransaction).filter(
            models.BankTransaction.id == tx_id
        ).with_for_update().first()

        if not tx:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch ngân hàng.")

        # Ngăn gửi lặp yêu cầu cho cùng một giao dịch
        existing_decision = db.query(models.Decision).filter(
            models.Decision.bank_transaction_id == tx.id,
            models.Decision.decision_type == models.DecisionType.OVERPAYMENT_RESOLUTION
        ).first()
        if existing_decision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Giao dịch {tx.reference_code} đã được ghi nhận phương thức xử lý tiền thừa trước đó."
            )

        matched_order = None
        if order_id:
            matched_order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if not matched_order:
            alloc = db.query(models.PaymentAllocation).filter(
                models.PaymentAllocation.bank_transaction_id == tx.id,
                models.PaymentAllocation.entry_type == models.EntryType.ALLOCATION
            ).first()
            if alloc:
                matched_order = db.query(models.Order).filter(models.Order.id == alloc.order_id).first()
        if not matched_order and tx.transfer_content:
            for word in (tx.transfer_content or "").upper().replace(",", " ").replace(".", " ").split():
                if word.startswith("ORD"):
                    matched_order = db.query(models.Order).filter(models.Order.order_code == word).first()
                    if matched_order:
                        break

        # Lưu quyết định xử lý tiền thừa vào DB (không làm sai lệch sổ cái hay hash-chain)
        decision_rec = models.Decision(
            order_id=matched_order.id if matched_order else None,
            bank_transaction_id=tx.id,
            reviewer_id=user.id,
            decision_type=models.DecisionType.OVERPAYMENT_RESOLUTION,
            reason=method_plan,
            challenge_used=challenge_used,
            assertion_signature=assertion_signature,
            biometric_verified=True
        )
        db.add(decision_rec)
        db.commit()
        db.refresh(decision_rec)

        return {
            "status": "success",
            "message": f"Đã ghi nhận phương thức xử lý khoản tiền thừa ({float(tx.unallocated_amount):,.0f} VNĐ) cho giao dịch {tx.reference_code}.",
            "decision_id": decision_rec.id,
            "bank_transaction_id": tx.id,
            "reference_code": tx.reference_code,
            "order_code": matched_order.order_code if matched_order else None,
            "unallocated_amount": float(tx.unallocated_amount),
            "handling_method": method_plan
        }

    raise HTTPException(status_code=400, detail="Loại quyết định không hợp lệ.")"""

assert target_reverse_end in dec_norm, "Target reverse end not found"
dec_norm = dec_norm.replace(target_reverse_end, replacement_reverse_end)

if "\r\n" in dec_code:
    dec_norm = dec_norm.replace("\n", "\r\n")

with open("backend/routers/decisions.py", "w", encoding="utf-8") as f:
    f.write(dec_norm)
print("SUCCESS: backend/routers/decisions.py updated")


# 2. Update backend/routers/dashboard.py
with open("backend/routers/dashboard.py", "r", encoding="utf-8") as f:
    dash_code = f.read()

dash_norm = dash_code.replace("\r\n", "\n")

target_dash_bank_tx = """    bank_tx_list = [
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
        })"""

replacement_dash_bank_tx = """    bank_tx_list = []
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

        is_ovp = bool(linked_order and float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0)
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
        })"""

assert target_dash_bank_tx in dash_norm, "Target dash bank tx not found"
dash_norm = dash_norm.replace(target_dash_bank_tx, replacement_dash_bank_tx)

if "\r\n" in dash_code:
    dash_norm = dash_norm.replace("\n", "\r\n")

with open("backend/routers/dashboard.py", "w", encoding="utf-8") as f:
    f.write(dash_norm)
print("SUCCESS: backend/routers/dashboard.py updated")
