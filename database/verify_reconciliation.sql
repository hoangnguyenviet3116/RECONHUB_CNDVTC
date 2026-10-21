-- [P1-11] Các câu truy vấn SQL kiểm chứng công thức đối soát tài chính

WITH ValidOrdersCTE AS (
    SELECT 
        shift_id,
        SUM(total_amount) AS valid_order_total
    FROM dbo.orders
    WHERE order_status IN ('CONFIRMED_ORDER', 'UNDER_REVIEW')
    GROUP BY shift_id
),
ActiveQRRequestsCTE AS (
    SELECT 
        o.shift_id,
        SUM(pr.expected_amount) AS active_qr_request_total
    FROM dbo.orders o
    INNER JOIN dbo.payment_requests pr ON o.id = pr.order_id
    WHERE o.order_status IN ('CONFIRMED_ORDER', 'UNDER_REVIEW')
      AND pr.status IN ('ACTIVE', 'FULFILLED') -- Loại trừ hoàn toàn REVOKED (20tr) và EXPIRED
    GROUP BY o.shift_id
),
NetAllocatedPaymentsCTE AS (
    SELECT 
        o.shift_id,
        SUM(pa.allocated_amount) AS allocated_payment_total -- Tự động bù trừ +ALLOCATION và -REVERSAL
    FROM dbo.orders o
    INNER JOIN dbo.payment_allocations pa ON o.id = pa.order_id
    WHERE o.order_status IN ('CONFIRMED_ORDER', 'UNDER_REVIEW')
    GROUP BY o.shift_id
),
UnallocatedBankTxCTE AS (
    SELECT 
        merchant_id,
        SUM(unallocated_amount) AS unallocated_bank_tx_total
    FROM dbo.bank_transactions
    WHERE match_status IN ('UNMATCHED', 'PARTIALLY_ALLOCATED')
    GROUP BY merchant_id
)
SELECT 
    s.id AS shift_id,
    s.name AS shift_name,
    s.target_revenue AS target_revenue,
    ISNULL(vo.valid_order_total, 0) AS valid_order_total,
    ISNULL(qr.active_qr_request_total, 0) AS active_qr_request_total,
    ISNULL(na.allocated_payment_total, 0) AS allocated_payment_total,
    (ISNULL(vo.valid_order_total, 0) - ISNULL(qr.active_qr_request_total, 0)) AS unissued_qr_amount,
    (ISNULL(qr.active_qr_request_total, 0) - ISNULL(na.allocated_payment_total, 0)) AS pending_qr_collection,
    (ISNULL(vo.valid_order_total, 0) - ISNULL(na.allocated_payment_total, 0)) AS remaining_receivable,
    ISNULL(ub.unallocated_bank_tx_total, 0) AS unallocated_bank_tx_total,
    (ISNULL(na.allocated_payment_total, 0) + ISNULL(ub.unallocated_bank_tx_total, 0)) AS total_bank_received
FROM dbo.shifts s
LEFT JOIN ValidOrdersCTE vo ON s.id = vo.shift_id
LEFT JOIN ActiveQRRequestsCTE qr ON s.id = qr.shift_id
LEFT JOIN NetAllocatedPaymentsCTE na ON s.id = na.shift_id
LEFT JOIN UnallocatedBankTxCTE ub ON s.merchant_id = ub.merchant_id
WHERE s.id = 1;

-- ---------------------------------------------------------------------------------
-- TRUY VẤN 2: BẢNG ĐỐI SOÁT CHI TIẾT TỪNG ĐƠN HÀNG TRONG CA 1
-- ---------------------------------------------------------------------------------
SELECT 
    o.id AS order_id,
    o.order_code,
    o.order_status,
    o.payment_status,
    o.total_amount,
    ISNULL(pr.request_code, 'NONE') AS active_qr_code,
    ISNULL(pr.status, 'NO_QR') AS qr_status,
    ISNULL(pr.expected_amount, 0) AS active_qr_amount,
    ISNULL(SUM(pa.allocated_amount), 0) AS net_paid_amount,
    CASE 
        WHEN o.order_status = 'CANCELLED_ORDER' THEN 0 
        ELSE (o.total_amount - ISNULL(SUM(pa.allocated_amount), 0)) 
    END AS order_remaining_amount
FROM dbo.orders o
LEFT JOIN dbo.payment_requests pr 
    ON o.id = pr.order_id AND pr.status IN ('ACTIVE', 'FULFILLED')
LEFT JOIN dbo.payment_allocations pa 
    ON o.id = pa.order_id
WHERE o.shift_id = 1
GROUP BY 
    o.id, o.order_code, o.order_status, o.payment_status, 
    o.total_amount, pr.request_code, pr.status, pr.expected_amount
ORDER BY o.id ASC;

-- ---------------------------------------------------------------------------------
-- TRUY VẤN 3: KIỂM TRA TÍNH TOÀN VẸN CHUỖI BĂM SỔ CÁI (VERIFY HASH CHAIN)
-- ---------------------------------------------------------------------------------
SELECT 
    cur.id,
    cur.bank_transaction_id,
    cur.payment_request_id,
    cur.order_id,
    cur.entry_type,
    cur.allocated_amount,
    cur.reversal_of_id,
    cur.prev_hash,
    cur.record_hash,
    CASE 
        WHEN cur.id = 1 AND cur.prev_hash = 'GENESIS_00000000000000000000000000000000000000000000000000000000' THEN 'VALID_GENESIS'
        WHEN cur.prev_hash = prev_row.record_hash THEN 'VALID_LINK'
        ELSE 'TAMPERED_BROKEN_LINK'
    END AS chain_link_status
FROM dbo.payment_allocations cur
LEFT JOIN dbo.payment_allocations prev_row ON cur.id = prev_row.id + 1
ORDER BY cur.id ASC;