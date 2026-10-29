import re
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

import models
from services.hash_chain_ledger import add_ledger_entry
from services.vietqr_service import generate_vietqr_url


# ==============================================================================
# TIER 1: CHUẨN HÓA VĂN BẢN VÀ BÙ LỖI QUANG HỌC / OCR / GÕ PHÍM (TYPO COMPENSATION)
# ==============================================================================

def normalize_optical_typos(suffix: str) -> str:
    """
    Sửa các lỗi nhầm lẫn quang học/gõ phím phổ biến:
    - Chữ 'O', 'Q' nhầm với số '0'
    - Chữ 'I', 'L' nhầm với số '1'
    - Chữ 'B' nhầm với số '8'
    - Chữ 'S' nhầm với số '5'
    - Chữ 'Z' nhầm với số '2'
    """
    trans_table = str.maketrans({
        'O': '0', 'Q': '0',
        'I': '1', 'L': '1',
        'B': '8',
        'S': '5',
        'Z': '2'
    })
    return suffix.upper().translate(trans_table)


def extract_candidate_order_codes(content: str) -> List[str]:
    """
    Phân tích nội dung chuyển khoản bằng Regex linh hoạt và sinh tập mã đơn hàng ứng viên.
    Hỗ trợ biến thể: ORD 1001, ORD-1001, ORD_1001, ORD1OO1, HD1001, DON 1001, v.v.
    """
    if not content:
        return []

    clean = content.upper()
    # Chuẩn hóa các dấu phân cách thông dụng
    for ch in [",", ".", ";", ":", "-", "_", "/", "#"]:
        clean = clean.replace(ch, " ")

    tokens = clean.split()
    candidates: List[str] = []

    # 1. Duyệt các cặp từ (ORD 1001, DON 1001, HD 1001)
    prefix_keywords = {"ORD", "HD", "DH", "DON", "BILL", "ORDER", "HOADON"}
    for i, t in enumerate(tokens):
        if t in prefix_keywords and i + 1 < len(tokens):
            next_token = tokens[i + 1]
            corrected = normalize_optical_typos(next_token)
            candidates.append(f"ORD{next_token}")
            candidates.append(f"ORD{corrected}")
            candidates.append(corrected)

    # 2. Duyệt các từ dính liền (ORD1001, ORD1OO1, HD1001)
    for t in tokens:
        for pfx in prefix_keywords:
            if t.startswith(pfx) and len(t) > len(pfx):
                suffix = t[len(pfx):]
                corrected = normalize_optical_typos(suffix)
                candidates.append(f"ORD{suffix}")
                candidates.append(f"ORD{corrected}")
                candidates.append(corrected)
                break
        # Nếu là chuỗi số dài từ 4 ký tự trở lên (ví dụ: 1001, 1002)
        if t.isdigit() and len(t) >= 4:
            candidates.append(f"ORD{t}")
            candidates.append(t)

    # Loại bỏ trùng lặp và giữ nguyên thứ tự xuất hiện
    return list(dict.fromkeys(candidates))


# ==============================================================================
# HELPER: PHÂN BỔ TIỀN VÀO ĐƠN HÀNG VÀ GHI SỔ CÁI HASH-CHAIN (REGTECH INTEGRITY)
# ==============================================================================

def get_order_remaining_amount(db: Session, order: models.Order) -> Decimal:
    """Tính số tiền còn phải thu của đơn hàng."""
    allocations = db.query(models.PaymentAllocation).filter(
        models.PaymentAllocation.order_id == order.id
    ).all()
    already_allocated = sum((Decimal(str(pa.allocated_amount)) for pa in allocations), Decimal("0.00"))
    order_total = Decimal(str(order.total_amount))
    return max(Decimal("0.00"), order_total - already_allocated)


def allocate_to_order(
    db: Session,
    bank_tx: models.BankTransaction,
    order: models.Order,
    alloc_amount: Optional[Decimal] = None,
    mode: models.AllocationMode = models.AllocationMode.AUTO
) -> Decimal:
    """
    Thực hiện phân bổ tài chính từ giao dịch ngân hàng vào một đơn hàng cụ thể:
    - Đảm bảo tính toàn vẹn trạng thái đơn hàng.
    - Cập nhật số tiền đã phân bổ/còn lại của giao dịch ngân hàng.
    - Tạo bản ghi sổ cái bất biến Hash-Chain Ledger theo tiêu chuẩn RegTech.
    """
    if order.order_status not in [models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW]:
        return Decimal("0.00")

    if order.payment_status == models.PaymentStatus.PAID:
        return Decimal("0.00")

    order_remaining = get_order_remaining_amount(db, order)
    if order_remaining <= Decimal("0.00"):
        return Decimal("0.00")

    unallocated_tx = Decimal(str(bank_tx.unallocated_amount))
    if unallocated_tx <= Decimal("0.00"):
        return Decimal("0.00")

    # Xác định số tiền phân bổ thực tế
    max_possible = min(unallocated_tx, order_remaining)
    actual_alloc = min(max_possible, alloc_amount) if alloc_amount is not None else max_possible

    if actual_alloc <= Decimal("0.00"):
        return Decimal("0.00")

    # Tìm hoặc tạo PaymentRequest ACTIVE cho đơn hàng
    active_qr = db.query(models.PaymentRequest).filter(
        models.PaymentRequest.order_id == order.id,
        models.PaymentRequest.status == models.PaymentRequestStatus.ACTIVE
    ).order_by(models.PaymentRequest.id.desc()).first()

    if not active_qr:
        active_qr = models.PaymentRequest(
            order_id=order.id,
            request_code=f"REQ_{order.order_code}_{uuid.uuid4().hex[:4].upper()}",
            expected_amount=order.total_amount,
            qr_url=generate_vietqr_url("970422", "0888999777", order.total_amount, order.order_code),
            status=models.PaymentRequestStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db.add(active_qr)
        db.flush()

    # Cập nhật số tiền trên giao dịch ngân hàng
    current_tx_allocated = Decimal(str(bank_tx.allocated_amount or "0.00"))
    bank_tx.allocated_amount = current_tx_allocated + actual_alloc
    bank_tx.unallocated_amount = unallocated_tx - actual_alloc

    if bank_tx.unallocated_amount == Decimal("0.00"):
        bank_tx.match_status = models.MatchStatus.FULLY_ALLOCATED
    else:
        bank_tx.match_status = models.MatchStatus.PARTIALLY_ALLOCATED

    # Cập nhật trạng thái đơn hàng và QR
    new_remaining = order_remaining - actual_alloc
    if new_remaining <= Decimal("0.00"):
        order.payment_status = models.PaymentStatus.PAID
        active_qr.status = models.PaymentRequestStatus.FULFILLED
    else:
        order.payment_status = models.PaymentStatus.PARTIALLY_PAID

    # Ghi nhận sổ cái bất biến Hash-Chain Ledger (Blockchain & RegTech Pillar)
    add_ledger_entry(
        db=db,
        bank_transaction_id=bank_tx.id,
        payment_request_id=active_qr.id,
        order_id=order.id,
        entry_type=models.EntryType.ALLOCATION,
        allocated_amount=actual_alloc,
        reversal_of_id=None,
        allocation_mode=mode
    )

    # Commit toàn bộ cập nhật (Order + BankTx + PaymentRequest + Ledger) trong cùng 1 transaction nguyên tử
    db.commit()

    return actual_alloc


# ==============================================================================
# TIER 2: RAPIDFUZZ MULTI-FACTOR CONFIDENCE SCORING (AI & RISK GOVERNANCE)
# ==============================================================================

def calculate_confidence_score(
    content: str,
    tx_amount: Decimal,
    tx_created_at: datetime,
    order: models.Order,
    order_remaining: Decimal
) -> float:
    """
    Tính toán Điểm tin cậy đa yếu tố (Multi-Factor Confidence Score) giữa GD và Đơn hàng:
    - Text Match (40%): Độ khớp nội dung chuyển khoản với Order Code, Note, Bàn.
    - Amount Match (45%): Độ khớp số tiền thanh toán với số tiền còn thiếu.
    - Time Match (15%): Khoảng cách thời gian tạo đơn và nhận tiền.
    """
    clean_content = (content or "").upper()
    order_code_clean = (order.order_code or "").upper()
    customer_note_clean = (order.customer_note or "").upper()

    # 1. Text Similarity Score (0.0 -> 1.0)
    score_code = fuzz.partial_ratio(order_code_clean, clean_content) / 100.0
    score_note = fuzz.token_set_ratio(customer_note_clean, clean_content) / 100.0 if customer_note_clean else 0.0
    text_score = max(score_code, score_note)

    # 2. Amount Similarity Score (0.0 -> 1.0)
    if order_remaining <= Decimal("0.00"):
        amount_score = 0.0
    else:
        diff = abs(tx_amount - order_remaining)
        if diff < Decimal("0.01"):
            amount_score = 1.0  # Khớp chính xác 100%
        elif tx_amount > order_remaining:
            # Khách chuyển thừa: vẫn có khả năng cao đúng đơn
            amount_score = 0.75
        else:
            # Khách chuyển thiếu: tỉ lệ số tiền
            ratio = float(tx_amount / order_remaining)
            amount_score = max(0.2, min(0.7, 0.4 + 0.3 * ratio))

    # 3. Time Proximity Score (0.0 -> 1.0)
    delta_seconds = abs((tx_created_at - order.created_at).total_seconds())
    if delta_seconds <= 300:        # <= 5 phút
        time_score = 1.0
    elif delta_seconds <= 1800:     # <= 30 phút
        time_score = 0.85
    elif delta_seconds <= 7200:     # <= 2 giờ
        time_score = 0.60
    elif delta_seconds <= 28800:    # <= 8 giờ (ca làm việc)
        time_score = 0.40
    else:
        time_score = 0.10

    # Trọng số tổng hợp
    composite = (0.40 * text_score) + (0.45 * amount_score) + (0.15 * time_score)
    return round(composite, 4)


# ==============================================================================
# TIER 3: SUBSET-SUM ENGINE CHO GIAO DỊCH CHUYỂN GỘP (BUNDLED TRANSFERS)
# ==============================================================================

def find_subset_sum_combinations(
    candidates: List[Tuple[models.Order, Decimal]],
    target: Decimal,
    max_solutions: int = 5
) -> List[List[models.Order]]:
    """
    Thuật toán Quy hoạch động / Nhánh cận (Branch & Bound Subset-Sum)
    tìm các tổ hợp đơn hàng có tổng số tiền còn thiếu bằng đúng số tiền nhận được.
    """
    valid = [(ord_obj, amt) for ord_obj, amt in candidates if Decimal("0.00") < amt <= target]
    # Sắp xếp giảm dần để tỉa nhánh sớm
    valid.sort(key=lambda x: x[1], reverse=True)

    solutions: List[List[models.Order]] = []

    def backtrack(start_idx: int, current_sum: Decimal, current_path: List[models.Order]):
        nonlocal solutions
        if len(solutions) >= max_solutions:
            return

        if current_sum == target:
            solutions.append(list(current_path))
            return

        for i in range(start_idx, len(valid)):
            ord_obj, amt = valid[i]
            if current_sum + amt > target:
                continue

            current_path.append(ord_obj)
            backtrack(i + 1, current_sum + amt, current_path)
            current_path.pop()

    backtrack(0, Decimal("0.00"), [])
    return solutions


# ==============================================================================
# PIPELINE ĐỐI SOÁT TỔNG THỂ (HYBRID MULTI-TIER ENGINE)
# ==============================================================================

def process_automatic_reconciliation(db: Session, bank_tx: models.BankTransaction):
    """
    Bộ máy Đối soát Đa tầng Kết hợp (Multi-Tier Hybrid Reconciliation Engine):
    - TIER 1: Regex linh hoạt & Bù lỗi gõ nhầm quang học (OCR/Typo Compensation).
    - TIER 2: AI Multi-Factor Confidence Scoring (RapidFuzz + Amount + Time).
    - TIER 3: Subset-Sum Engine giải quyết bài toán khách chuyển gộp nhiều đơn.
    - REGTECH GOVERNANCE: Tuân thủ quy tắc không tự ý đoán mò khi có xung đột,
      tự động chuyển trạng thái UNDER_REVIEW để con người thẩm duyệt bảo mật.
    """
    if Decimal(str(bank_tx.unallocated_amount)) <= Decimal("0.00"):
        return

    content = bank_tx.transfer_content or ""
    tx_created = bank_tx.created_at or datetime.utcnow()

    # Lấy danh sách các đơn hàng chưa hoàn tất thanh toán trong hệ thống
    open_orders_query = db.query(models.Order).filter(
        models.Order.payment_status.in_([models.PaymentStatus.UNPAID, models.PaymentStatus.PARTIALLY_PAID]),
        models.Order.order_status.in_([models.OrderStatus.CONFIRMED_ORDER, models.OrderStatus.UNDER_REVIEW])
    ).order_by(models.Order.id.desc())

    open_orders = open_orders_query.all()
    if not open_orders:
        return

    # -------------------------------------------------------------------------
    # TIER 1: REGEX & OPTICAL TYPO NORMALIZATION
    # -------------------------------------------------------------------------
    candidate_codes = extract_candidate_order_codes(content)
    tier1_matched_orders: List[models.Order] = []

    if candidate_codes:
        # Tìm các đơn hàng khớp với các mã ứng viên
        for ord_cand in open_orders:
            if ord_cand.order_code in candidate_codes or ord_cand.order_code.upper() in candidate_codes:
                if ord_cand not in tier1_matched_orders:
                    tier1_matched_orders.append(ord_cand)

    # Nếu Tier 1 tìm thấy khớp mã đơn hàng:
    if tier1_matched_orders:
        if len(tier1_matched_orders) == 1:
            # Khớp duy nhất 1 đơn hàng qua mã chuẩn hóa/sửa lỗi typo
            target_order = tier1_matched_orders[0]
            allocate_to_order(db, bank_tx, target_order, mode=models.AllocationMode.AUTO)
            return
        else:
            # Khách hàng chuyển gộp ghi rõ nhiều mã đơn (ví dụ: "TT ORD1001 VA ORD1002")
            for ord_target in tier1_matched_orders:
                if Decimal(str(bank_tx.unallocated_amount)) <= Decimal("0.00"):
                    break
                allocate_to_order(db, bank_tx, ord_target, mode=models.AllocationMode.AUTO)
            return

    # -------------------------------------------------------------------------
    # TIER 2: RAPIDFUZZ MULTI-FACTOR CONFIDENCE SCORING
    # -------------------------------------------------------------------------
    scored_candidates = []
    for ord_cand in open_orders:
        rem_amt = get_order_remaining_amount(db, ord_cand)
        if rem_amt <= Decimal("0.00"):
            continue
        score = calculate_confidence_score(
            content=content,
            tx_amount=Decimal(str(bank_tx.unallocated_amount)),
            tx_created_at=tx_created,
            order=ord_cand,
            order_remaining=rem_amt
        )
        scored_candidates.append((ord_cand, rem_amt, score))

    scored_candidates.sort(key=lambda x: x[2], reverse=True)

    if scored_candidates:
        top_order, top_rem, top_score = scored_candidates[0]
        second_score = scored_candidates[1][2] if len(scored_candidates) > 1 else 0.0

        # Nếu độ tin cậy vượt ngưỡng cao (>= 0.90) và vượt trội so với đơn thứ hai
        if top_score >= 0.90 and (top_score - second_score >= 0.15):
            allocate_to_order(db, bank_tx, top_order, mode=models.AllocationMode.AUTO)
            return

        # Nếu độ tin cậy ở mức nghi ngờ hợp lý (0.60 <= score < 0.90):
        # Không tự đoán mò mà đánh dấu UNDER_REVIEW để nhân viên xác nhận tại màn hình Đối soát
        if top_score >= 0.60:
            top_order.order_status = models.OrderStatus.UNDER_REVIEW
            db.commit()

    # -------------------------------------------------------------------------
    # TIER 3: SUBSET-SUM ENGINE CHO GIAO DỊCH CHUYỂN GỘP (BUNDLED TRANSFERS)
    # -------------------------------------------------------------------------
    unalloc_tx = Decimal(str(bank_tx.unallocated_amount))
    if unalloc_tx > Decimal("0.00"):
        subset_candidates = []
        for ord_cand in open_orders:
            rem = get_order_remaining_amount(db, ord_cand)
            if Decimal("0.00") < rem <= unalloc_tx:
                subset_candidates.append((ord_cand, rem))

        if subset_candidates:
            combinations = find_subset_sum_combinations(subset_candidates, unalloc_tx, max_solutions=3)

            # Quy tắc an toàn Quản trị rủi ro:
            # Chỉ tự động phân bổ khi tìm thấy DUY NHẤT 1 tổ hợp khớp tuyệt đối tổng tiền (1 <= số đơn <= 4)
            if len(combinations) == 1 and 1 <= len(combinations[0]) <= 4:
                matched_combo = combinations[0]
                for ord_in_combo in matched_combo:
                    if Decimal(str(bank_tx.unallocated_amount)) <= Decimal("0.00"):
                        break
                    rem_target = get_order_remaining_amount(db, ord_in_combo)
                    allocate_to_order(db, bank_tx, ord_in_combo, alloc_amount=rem_target, mode=models.AllocationMode.AUTO)
                return
            elif len(combinations) > 1:
                # Có nhiều hơn 1 tổ hợp đơn hàng cho cùng số tiền -> Rủi ro nhầm lẫn!
                # Đánh dấu các đơn hàng liên quan là UNDER_REVIEW để con người xử lý
                for combo in combinations:
                    for ord_item in combo:
                        ord_item.order_status = models.OrderStatus.UNDER_REVIEW
                db.commit()
