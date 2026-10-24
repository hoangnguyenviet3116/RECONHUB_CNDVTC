import hashlib
from typing import List, Tuple, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
import models


def hash_pair(left: str, right: str) -> str:
    """Băm một cặp nút lá/nút trung gian thành nút cha trong Cây Merkle nhị phân."""
    raw = f"{left}{right}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_merkle_tree(leaf_hashes: List[str]) -> Tuple[str, List[List[str]]]:
    """
    Xây dựng cây Merkle nhị phân (Binary Merkle Tree) từ danh sách các leaf_hashes.
    Nếu danh sách rỗng, trả về mã băm đặc biệt của ca rỗng.
    Trả về: (merkle_root, tree_levels)
    """
    if not leaf_hashes:
        empty_root = hashlib.sha256(b"EMPTY_SHIFT_NO_ALLOCATIONS").hexdigest()
        return empty_root, []

    current_level = list(leaf_hashes)
    levels = [current_level]

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            if i + 1 < len(current_level):
                right = current_level[i + 1]
            else:
                right = left  # Chuẩn nhân đôi nút lẻ (Duplication) như Bitcoin/Ethereum
            next_level.append(hash_pair(left, right))
        levels.append(next_level)
        current_level = next_level

    return current_level[0], levels


def get_merkle_proof(leaf_index: int, tree_levels: List[List[str]]) -> List[Dict[str, str]]:
    """
    Sinh đường dẫn bằng chứng mật mã (Merkle Proof Path) cho một nút lá tại leaf_index.
    Độ phức tạp O(log N).
    """
    if not tree_levels or leaf_index >= len(tree_levels[0]):
        return []

    proof = []
    idx = leaf_index
    for level_idx in range(len(tree_levels) - 1):
        level = tree_levels[level_idx]
        if idx % 2 == 0:
            # Sibling nằm bên phải
            sibling = level[idx + 1] if idx + 1 < len(level) else level[idx]
            proof.append({"position": "right", "hash": sibling})
        else:
            # Sibling nằm bên trái
            sibling = level[idx - 1]
            proof.append({"position": "left", "hash": sibling})
        idx = idx // 2

    return proof


def verify_merkle_proof(leaf_hash: str, proof: List[Dict[str, str]], expected_root: str) -> bool:
    """
    Kiểm toán độc lập: Xác minh một bút toán (leaf_hash) có thực sự thuộc về Merkle Root chốt ca hay không.
    """
    current = leaf_hash
    for item in proof:
        pos = item.get("position", "right")
        sibling = item.get("hash", "")
        if pos == "right":
            current = hash_pair(current, sibling)
        else:
            current = hash_pair(sibling, current)
    return current == expected_root


def generate_shift_merkle_audit(
    db: Session,
    shift: models.Shift,
    closed_by_user_id: Optional[int] = None
) -> models.ShiftAudit:
    """
    Tạo chứng chỉ kiểm toán Merkle chốt ca (Shift Settlement Merkle Audit):
    1. Thu thập toàn bộ các đơn hàng thuộc ca.
    2. Thu thập toàn bộ bút toán PaymentAllocation phát sinh cho các đơn hàng đó.
    3. Trích xuất leaf_hashes = record_hash của từng bút toán.
    4. Tính Merkle Root đại diện bất biến cho ca làm việc.
    5. Lưu hoặc cập nhật bản ghi ShiftAudit.
    """
    orders = db.query(models.Order).filter(models.Order.shift_id == shift.id).all()
    order_ids = [o.id for o in orders]

    allocations = []
    if order_ids:
        allocations = db.query(models.PaymentAllocation).filter(
            models.PaymentAllocation.order_id.in_(order_ids)
        ).order_by(models.PaymentAllocation.id.asc()).all()

    leaf_hashes = [pa.record_hash for pa in allocations]
    merkle_root, _ = build_merkle_tree(leaf_hashes)

    total_revenue = sum((Decimal(str(o.total_amount)) for o in orders), Decimal("0.00"))
    now_dt = datetime.utcnow()
    audit_sig = f"MERKLE_PROOF_SHIFT_{shift.id}_{merkle_root[:16]}_{now_dt.strftime('%Y%m%d%H%M%S')}"

    shift_audit = db.query(models.ShiftAudit).filter(models.ShiftAudit.shift_id == shift.id).first()
    if not shift_audit:
        shift_audit = models.ShiftAudit(
            shift_id=shift.id,
            merchant_id=shift.merchant_id or 1,
            closed_by=closed_by_user_id,
            total_orders=len(orders),
            total_revenue=total_revenue,
            total_allocations=len(allocations),
            merkle_root=merkle_root,
            first_record_hash=leaf_hashes[0] if leaf_hashes else None,
            last_record_hash=leaf_hashes[-1] if leaf_hashes else None,
            audit_signature=audit_sig,
            created_at=now_dt
        )
        db.add(shift_audit)
    else:
        shift_audit.closed_by = closed_by_user_id or shift_audit.closed_by
        shift_audit.total_orders = len(orders)
        shift_audit.total_revenue = total_revenue
        shift_audit.total_allocations = len(allocations)
        shift_audit.merkle_root = merkle_root
        shift_audit.first_record_hash = leaf_hashes[0] if leaf_hashes else None
        shift_audit.last_record_hash = leaf_hashes[-1] if leaf_hashes else None
        shift_audit.audit_signature = audit_sig
        shift_audit.created_at = now_dt

    db.commit()
    db.refresh(shift_audit)
    return shift_audit
