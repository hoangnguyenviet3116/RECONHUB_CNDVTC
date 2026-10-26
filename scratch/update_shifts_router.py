with open("backend/routers/shifts.py", "r", encoding="utf-8") as f:
    code = f.read()

merkle_endpoints = """

# ==============================================================================
# TRỤ CỘT BLOCKCHAIN & REGTECH: CÂY MERKLE CHỐT CA & KIỂM TOÁN ĐỘC LẬP
# ==============================================================================
from services.merkle_tree import (
    build_merkle_tree,
    get_merkle_proof,
    verify_merkle_proof,
    generate_shift_merkle_audit
)


@router.get("/{shift_id}/merkle-audit")
def get_shift_merkle_audit_endpoint(
    shift_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    \"\"\"
    Trả về chứng chỉ kiểm toán Merkle Tree của ca làm việc (Merkle Root Hash, Sổ cái bút toán).
    \"\"\"
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy ca #{shift_id}.")

    shift_audit = db.query(models.ShiftAudit).filter(models.ShiftAudit.shift_id == shift_id).first()
    if not shift_audit:
        shift_audit = generate_shift_merkle_audit(db=db, shift=shift)

    orders = db.query(models.Order).filter(models.Order.shift_id == shift.id).all()
    order_ids = [o.id for o in orders]
    allocs = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id.in_(order_ids)
    ).order_by(models.PaymentAllocation.id.asc()).all() if order_ids else []

    leaves = [
        {
            "allocation_id": a.id,
            "order_id": a.order_id,
            "bank_transaction_id": a.bank_transaction_id,
            "allocated_amount": float(a.allocated_amount),
            "record_hash": a.record_hash,
            "prev_hash": a.prev_hash,
            "created_at": a.created_at
        }
        for a in allocs
    ]

    return {
        "shift_id": shift.id,
        "shift_name": shift.name,
        "shift_status": shift.status.value if hasattr(shift.status, "value") else str(shift.status),
        "merkle_root": shift_audit.merkle_root,
        "total_orders": shift_audit.total_orders,
        "total_revenue": float(shift_audit.total_revenue),
        "total_allocations": shift_audit.total_allocations,
        "first_record_hash": shift_audit.first_record_hash,
        "last_record_hash": shift_audit.last_record_hash,
        "audit_signature": shift_audit.audit_signature,
        "closed_by": shift_audit.closed_by,
        "created_at": shift_audit.created_at,
        "leaf_count": len(leaves),
        "leaves": leaves
    }


@router.post("/{shift_id}/verify-merkle-proof")
def verify_shift_merkle_proof_endpoint(
    shift_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user_info: dict = Depends(verify_merchant_user)
):
    \"\"\"
    Kiểm toán độc lập: Xác minh một hóa đơn / bút toán (qua record_hash hoặc allocation_id)
    có nằm trong Merkle Root của ca hay không qua đường dẫn Merkle Proof O(log N).
    \"\"\"
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy ca #{shift_id}.")

    shift_audit = db.query(models.ShiftAudit).filter(models.ShiftAudit.shift_id == shift_id).first()
    if not shift_audit:
        shift_audit = generate_shift_merkle_audit(db=db, shift=shift)

    orders = db.query(models.Order).filter(models.Order.shift_id == shift.id).all()
    order_ids = [o.id for o in orders]
    allocs = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id.in_(order_ids)
    ).order_by(models.PaymentAllocation.id.asc()).all() if order_ids else []

    leaf_hashes = [a.record_hash for a in allocs]
    merkle_root, levels = build_merkle_tree(leaf_hashes)

    target_hash = payload.get("record_hash")
    target_alloc_id = payload.get("allocation_id")

    if target_alloc_id and not target_hash:
        target_alloc = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.id == target_alloc_id
        ).first()
        if target_alloc:
            target_hash = target_alloc.record_hash

    if not target_hash:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp record_hash hoặc allocation_id cần kiểm toán.")

    if target_hash not in leaf_hashes:
        return {
            "verified": False,
            "message": f"Mã băm bút toán {target_hash[:16]}... không thuộc về ca làm việc #{shift_id}.",
            "leaf_hash": target_hash,
            "merkle_root": merkle_root,
            "proof": []
        }

    leaf_index = leaf_hashes.index(target_hash)
    proof = get_merkle_proof(leaf_index, levels)
    is_valid = verify_merkle_proof(target_hash, proof, merkle_root)

    return {
        "verified": is_valid,
        "message": "Bút toán hợp lệ tuyệt đối trên Cây Merkle chốt ca." if is_valid else "Mã băm không khớp Merkle Root.",
        "leaf_hash": target_hash,
        "leaf_index": leaf_index,
        "merkle_root": merkle_root,
        "proof": proof
    }
"""

if "verify_shift_merkle_proof_endpoint" not in code:
    code += merkle_endpoints
    with open("backend/routers/shifts.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: backend/routers/shifts.py updated with Merkle Audit endpoints!")
else:
    print("Merkle endpoints already present in shifts.py")
