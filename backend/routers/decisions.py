from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime
import models
from database import get_db
from dependencies import verify_merchant_user
from services.hash_chain_ledger import add_ledger_entry
from services.webauthn_verifier import (
    verify_webauthn_assertion,
    verify_webauthn_registration,
    generate_user_challenge,
)

router = APIRouter(
    prefix="/decisions",
    tags=["Decisions & WebAuthn"],
    dependencies=[Depends(verify_merchant_user)]
)


@router.get("/")
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
    ]


@router.get("/allocations")
def get_all_allocations(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    allocs = db.query(models.PaymentAllocation).order_by(models.PaymentAllocation.id.desc()).all()
    reversed_ids = {
        a.reversal_of_id for a in allocs if a.reversal_of_id is not None
    }
    results = []
    for a in allocs:
        tx = db.query(models.BankTransaction).filter(models.BankTransaction.id == a.bank_transaction_id).first()
        order = db.query(models.Order).filter(models.Order.id == a.order_id).first()
        entry_str = a.entry_type.value if hasattr(a.entry_type, "value") else str(a.entry_type)
        results.append({
            "id": a.id,
            "bank_transaction_id": a.bank_transaction_id,
            "reference_code": tx.reference_code if tx else f"TX#{a.bank_transaction_id}",
            "transfer_content": tx.transfer_content if tx else "",
            "payment_request_id": a.payment_request_id,
            "order_id": a.order_id,
            "order_code": order.order_code if order else f"ORD#{a.order_id}",
            "entry_type": entry_str,
            "allocated_amount": float(a.allocated_amount),
            "reversal_of_id": a.reversal_of_id,
            "is_reversed": a.id in reversed_ids,
            "allocation_mode": a.allocation_mode.value if hasattr(a.allocation_mode, "value") else str(a.allocation_mode),
            "prev_hash": a.prev_hash,
            "record_hash": a.record_hash,
            "created_at": a.created_at
        })
    return results


@router.post("/challenge")
@router.post("/webauthn/authenticate/options")
def request_webauthn_challenge(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    user = db.query(models.User).filter(models.User.id == user_info["user_id"]).first()
    if not user:
        user = db.query(models.User).order_by(models.User.id.asc()).first()

    challenge = generate_user_challenge(db, user)
    return {
        "user_id": user.id,
        "challenge": challenge,
        "rpId": "localhost",
        "allowCredentials": [
            {
                "id": user.webauthn_credential_id or f"CRED_USER_{user.id}",
                "type": "public-key"
            }
        ],
        "expires_in_seconds": 300
    }


@router.post("/webauthn/register/options")
def request_webauthn_register_options(
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    user = db.query(models.User).filter(models.User.id == user_info["user_id"]).first()
    if not user:
        user = db.query(models.User).order_by(models.User.id.asc()).first()

    challenge = generate_user_challenge(db, user)
    return {
        "challenge": challenge,
        "rp": {"name": "VietQR ReconHub", "id": "localhost"},
        "user": {
            "id": str(user.id),
            "name": user.email,
            "displayName": user.full_name
        },
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}]
    }


@router.post("/webauthn/register/verify")
def verify_webauthn_register(
    reg_data: dict,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    user = db.query(models.User).filter(models.User.id == user_info["user_id"]).first()
    if not user:
        user = db.query(models.User).order_by(models.User.id.asc()).first()

    result = verify_webauthn_registration(
        db=db,
        user=user,
        challenge_used=reg_data.get("challenge_used") or reg_data.get("challenge"),
        credential_id=reg_data.get("credential_id") or f"CRED_USER_{user.id}",
        public_key=reg_data.get("public_key", "PUBKEY_WEBAUTHN_ECDSA_P256")
    )
    if not result["verified"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/")
def make_decision(
    decision_data: dict,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    if user_info["role"] not in ["REVIEWER", "OWNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện xét duyệt ngoại lệ (Chỉ REVIEWER hoặc OWNER)."
        )

    user = db.query(models.User).filter(models.User.id == user_info["user_id"]).first()
    if not user:
        user = db.query(models.User).order_by(models.User.id.asc()).first()

    challenge_used = decision_data.get("challenge_used") or decision_data.get("challenge")
    assertion_signature = decision_data.get("assertion_signature") or decision_data.get("signature")
    credential_id = decision_data.get("credential_id")
    is_demo = decision_data.get("is_demo", True)
    security_mode = decision_data.get("security_mode")

    auth_result = verify_webauthn_assertion(
        db=db,
        user=user,
        challenge_used=challenge_used,
        assertion_signature=assertion_signature,
        credential_id=credential_id,
        is_demo_mode=is_demo,
        security_mode=security_mode
    )

    if not auth_result["verified"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Xác thực sinh trắc học thất bại: {auth_result['message']}"
        )

    order_id = decision_data.get("order_id")
    tx_id = decision_data.get("bank_transaction_id")
    decision_type = decision_data.get("decision_type")
    reason = str(decision_data.get("reason", "Phân bổ / Đảo bút toán ngoại lệ")).strip()

    if not reason:
        raise HTTPException(status_code=400, detail="Vui lòng nhập lý do xử lý ngoại lệ.")

    if decision_type == "APPROVE_MANUAL_MATCH":
        if not order_id or not tx_id:
            raise HTTPException(status_code=400, detail="Thiếu thông tin order_id hoặc bank_transaction_id.")

        tx = db.query(models.BankTransaction).filter(
            models.BankTransaction.id == tx_id
        ).with_for_update().first()

        if not tx:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch ngân hàng.")

        order = db.query(models.Order).filter(
            models.Order.id == order_id
        ).with_for_update().first()

        if not order:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

        if order.order_status not in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]:
            raise HTTPException(status_code=400, detail="Đơn hàng đã hủy hoặc không hợp lệ để phân bổ.")

        if order.payment_status == models.PaymentStatus.PAID:
            raise HTTPException(status_code=400, detail="Đơn hàng này đã được thanh toán đầy đủ.")

        active_qr = db.query(models.PaymentRequest).filter(
            models.PaymentRequest.order_id == order.id,
            models.PaymentRequest.status == models.PaymentRequestStatus.ACTIVE
        ).first()

        if not active_qr:
            # Nếu đơn hợp lệ chưa xuất QR thì tự động tạo yêu cầu thu QR để gắn sổ cái
            from services.vietqr_service import generate_vietqr_url
            import uuid
            active_qr = models.PaymentRequest(
                order_id=order.id,
                request_code=f"REQ_{order.order_code}_{uuid.uuid4().hex[:4].upper()}",
                expected_amount=order.total_amount,
                qr_url=generate_vietqr_url("970422", "0888999777", order.total_amount, order.order_code),
                status=models.PaymentRequestStatus.ACTIVE,
                expires_at=datetime.utcnow()
            )
            db.add(active_qr)
            db.flush()

        allocations = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.order_id == order.id
        ).all()
        already_allocated = sum((Decimal(str(pa.allocated_amount)) for pa in allocations), Decimal("0.00"))
        order_remaining = Decimal(str(order.total_amount)) - already_allocated

        if order_remaining <= Decimal("0.00"):
            raise HTTPException(status_code=400, detail="Đơn hàng không còn số tiền phải thu.")

        unallocated_tx = Decimal(str(tx.unallocated_amount))
        if unallocated_tx <= Decimal("0.00"):
            raise HTTPException(status_code=400, detail="Giao dịch ngân hàng đã hết tiền chưa phân bổ.")

        requested_amt = decision_data.get("amount") or decision_data.get("allocated_amount")
        alloc_amount = min(unallocated_tx, order_remaining)
        if requested_amt is not None:
            req_dec = Decimal(str(requested_amt))
            if req_dec > Decimal("0.00"):
                alloc_amount = min(alloc_amount, req_dec)

        tx.allocated_amount = Decimal(str(tx.allocated_amount or "0.00")) + alloc_amount
        tx.unallocated_amount = unallocated_tx - alloc_amount
        if tx.unallocated_amount == Decimal("0.00"):
            tx.match_status = models.MatchStatus.FULLY_ALLOCATED
        else:
            tx.match_status = models.MatchStatus.PARTIALLY_ALLOCATED

        new_total_allocated = already_allocated + alloc_amount
        if new_total_allocated >= Decimal(str(order.total_amount)):
            order.payment_status = models.PaymentStatus.PAID
            active_qr.status = models.PaymentRequestStatus.FULFILLED
        else:
            order.payment_status = models.PaymentStatus.PARTIALLY_PAID

        new_alloc = add_ledger_entry(
            db=db,
            bank_transaction_id=tx.id,
            payment_request_id=active_qr.id,
            order_id=order.id,
            entry_type=models.EntryType.ALLOCATION,
            allocated_amount=alloc_amount,
            reversal_of_id=None,
            allocation_mode=models.AllocationMode.MANUAL
        )

        decision_rec = models.Decision(
            order_id=order.id,
            bank_transaction_id=tx.id,
            reviewer_id=user.id,
            decision_type=models.DecisionType.APPROVE_MANUAL_MATCH,
            reason=reason,
            challenge_used=challenge_used,
            assertion_signature=assertion_signature,
            biometric_verified=True
        )
        db.add(decision_rec)
        db.commit()

        return {
            "status": "success",
            "message": f"Phân bổ thủ công thành công {alloc_amount:,.0f} VNĐ vào đơn {order.order_code}.",
            "allocation_id": new_alloc.id,
            "decision_id": decision_rec.id
        }

    elif decision_type == "REVERSE_ALLOCATION":
        target_allocation_id = decision_data.get("allocation_id") or decision_data.get("target_allocation_id")
        if not target_allocation_id:
            raise HTTPException(status_code=400, detail="Thiếu allocation_id cần đảo bút toán.")

        orig_alloc = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.id == target_allocation_id,
            models.PaymentAllocation.entry_type == models.EntryType.ALLOCATION
        ).first()

        if not orig_alloc:
            raise HTTPException(status_code=404, detail="Không tìm thấy bút toán phân bổ gốc.")

        existing_reversal = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.reversal_of_id == orig_alloc.id
        ).first()
        if existing_reversal:
            raise HTTPException(status_code=400, detail="Bút toán này đã được đảo trước đó, không thể đảo lần nữa.")

        orig_amount = Decimal(str(orig_alloc.allocated_amount))

        orig_tx = db.query(models.BankTransaction).filter(
            models.BankTransaction.id == orig_alloc.bank_transaction_id
        ).with_for_update().first()

        if orig_tx:
            orig_tx.allocated_amount = Decimal(str(orig_tx.allocated_amount)) - orig_amount
            orig_tx.unallocated_amount = Decimal(str(orig_tx.unallocated_amount)) + orig_amount
            if orig_tx.allocated_amount <= Decimal("0.00"):
                orig_tx.match_status = models.MatchStatus.UNMATCHED
            else:
                orig_tx.match_status = models.MatchStatus.PARTIALLY_ALLOCATED

        orig_order = db.query(models.Order).filter(
            models.Order.id == orig_alloc.order_id
        ).with_for_update().first()

        if orig_order:
            all_allocs = db.query(models.PaymentAllocation).filter(
                models.PaymentAllocation.order_id == orig_order.id
            ).all()
            net_allocated_after = sum((Decimal(str(pa.allocated_amount)) for pa in all_allocs), Decimal("0.00")) - orig_amount

            order_total = Decimal(str(orig_order.total_amount))
            if net_allocated_after <= Decimal("0.00"):
                orig_order.payment_status = models.PaymentStatus.UNPAID
            elif net_allocated_after < order_total:
                orig_order.payment_status = models.PaymentStatus.PARTIALLY_PAID
            else:
                orig_order.payment_status = models.PaymentStatus.PAID

            qr = db.query(models.PaymentRequest).filter(
                models.PaymentRequest.id == orig_alloc.payment_request_id
            ).first()

            if qr and net_allocated_after < Decimal(str(qr.expected_amount)):
                if (
                    orig_order.order_status in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]
                    and qr.status == models.PaymentRequestStatus.FULFILLED
                    and qr.expires_at > datetime.utcnow()
                ):
                    qr.status = models.PaymentRequestStatus.ACTIVE

        reversal_alloc = add_ledger_entry(
            db=db,
            bank_transaction_id=orig_alloc.bank_transaction_id,
            payment_request_id=orig_alloc.payment_request_id,
            order_id=orig_alloc.order_id,
            entry_type=models.EntryType.REVERSAL,
            allocated_amount=-orig_amount,
            reversal_of_id=orig_alloc.id,
            allocation_mode=models.AllocationMode.REVERSAL
        )

        decision_rec = models.Decision(
            order_id=orig_alloc.order_id,
            bank_transaction_id=orig_alloc.bank_transaction_id,
            reviewer_id=user.id,
            decision_type=models.DecisionType.REVERSE_ALLOCATION,
            reason=reason,
            challenge_used=challenge_used,
            assertion_signature=assertion_signature,
            biometric_verified=True
        )
        db.add(decision_rec)
        db.commit()

        return {
            "status": "success",
            "message": f"Đảo bút toán #{orig_alloc.id} thành công (-{orig_amount:,.0f} VNĐ).",
            "reversal_allocation_id": reversal_alloc.id,
            "decision_id": decision_rec.id
        }

    raise HTTPException(status_code=400, detail="Loại quyết định không hợp lệ.")