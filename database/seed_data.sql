-- [P1-06] Script nạp dữ liệu mẫu chuẩn: 100tr đơn hợp lệ / 90tr QR / 75tr đã phân bổ / 5tr tiền treo
-- KỊCH BẢN SỐ LIỆU CHUẨN TRONG CA 1:
--   • Mục tiêu doanh thu tham khảo (target_revenue) : 120.000.000 VNĐ
--   • Tổng giá trị đơn hàng hợp lệ (Valid Order)    : 100.000.000 VNĐ (5 đơn CONFIRMED_ORDER)
--   • Giá trị yêu cầu thu QR hiệu lực (Active QR)   :  90.000.000 VNĐ (Loại trừ 1 QR REVOKED 20tr)
--   • Tiền thực thu ròng đã phân bổ (Net Allocated) :  75.000.000 VNĐ (Chuỗi băm SHA-256 nối tiếp)
--   • Tiền ngân hàng chưa phân bổ (Unallocated Tx)  :   5.000.000 VNĐ (1 GD sai mã đơn UNMATCHED)
-- ==================================================================================================

SET NOCOUNT ON;
BEGIN TRANSACTION;

-- 1. XÓA SẠCH DỮ LIỆU CŨ & RESET BỘ ĐẾM IDENTITY VỀ 1 (ĐỂ DEMO LẠI NHIỀU LẦN)
DELETE FROM dbo.decisions;
DELETE FROM dbo.payment_allocations;
DELETE FROM dbo.bank_transactions;
DELETE FROM dbo.payment_requests;
DELETE FROM dbo.orders;
DELETE FROM dbo.shifts;
DELETE FROM dbo.merchant_users;
DELETE FROM dbo.merchants;
DELETE FROM dbo.users;

--đặt lại giá trị tự tăng (IDENTITY) của các bảng trong SQL Server về 0
DBCC CHECKIDENT ('dbo.decisions', RESEED, 0);
DBCC CHECKIDENT ('dbo.payment_allocations', RESEED, 0);
DBCC CHECKIDENT ('dbo.bank_transactions', RESEED, 0);
DBCC CHECKIDENT ('dbo.payment_requests', RESEED, 0);
DBCC CHECKIDENT ('dbo.orders', RESEED, 0);
DBCC CHECKIDENT ('dbo.shifts', RESEED, 0);
DBCC CHECKIDENT ('dbo.merchant_users', RESEED, 0);
DBCC CHECKIDENT ('dbo.merchants', RESEED, 0);
DBCC CHECKIDENT ('dbo.users', RESEED, 0);

-- 2. NẠP BẢNG users (3 Tài khoản đại diện cho 3 vai trò trong cửa hàng)
INSERT INTO dbo.users (full_name, email, password_hash, webauthn_credential_id, webauthn_public_key, current_challenge) VALUES
(N'Nguyễn Việt Hoàng (Thu Ngân POS)', 'cashier@reconhub.vn', 'hashed_pw_123', NULL, NULL, NULL),
(N'Trần Thu Thảo (Kế Toán Đối Soát)', 'reviewer@reconhub.vn', 'hashed_pw_123', 'CRED_DEMO_REVIEWER_01', 'PUBKEY_DEMO_ECDSA_P256', NULL),
(N'Lê Hồng Hạnh (Chủ Cửa Hàng)', 'owner@reconhub.vn', 'hashed_pw_123', 'CRED_DEMO_OWNER_01', 'PUBKEY_DEMO_ECDSA_P256', NULL);

-- 3. NẠP BẢNG merchants (1 Hộ kinh doanh / Cửa hàng MVP)
INSERT INTO dbo.merchants (merchant_code, name, bank_bin, account_no, webhook_secret) VALUES
('MC_RECON_01', N'VietQR ReconHub Flagship Store - Hà Nội', '970422', '0888999777', 'RECONHUB_HMAC_SECRET_2026');

-- 4. NẠP BẢNG merchant_users (Phân quyền nhân sự thuộc cửa hàng: CASHIER, REVIEWER, OWNER)
INSERT INTO dbo.merchant_users (user_id, merchant_id, role, is_active) VALUES
    (0, 0, 'CASHIER', 1),
    (1, 0, 'REVIEWER', 1),
    (2, 0, 'OWNER', 1);

-- 5. NẠP BẢNG shifts (Ca 1 đang OPEN có target_revenue = 120.000.000 VNĐ chỉ làm chỉ tiêu tham khảo)
INSERT INTO dbo.shifts (merchant_id, name, target_revenue, start_time, end_time, status) VALUES
(0, N'Ca Kinh Doanh Chính - Ngày 24/10/2026', 120000000.00, '2026-10-24 08:00:00', '2026-10-24 22:00:00', 'OPEN'),
(0, N'Ca Dự Phòng Ngày Mai - 25/10/2026', 80000000.00, '2026-10-25 08:00:00', '2026-10-25 22:00:00', 'DRAFT');

-- 6. NẠP BẢNG orders
-- 5 Đơn hợp lệ (CONFIRMED_ORDER) có tổng = 40tr + 25tr + 15tr + 10tr + 10tr = 100.000.000 VNĐ
-- 1 Đơn đã hủy (CANCELLED_ORDER = 8tr) để kiểm chứng công thức KHÔNG cộng đơn hủy vào Valid Order Total
INSERT INTO dbo.orders (shift_id, created_by, order_code, total_amount, customer_note, order_status, payment_status, created_at) VALUES
(1, 1, 'ORD1001', 40000000.00, N'Đơn hàng thiết bị POS Lô A - Đã thu đủ 40tr', 'CONFIRMED_ORDER', 'PAID', '2026-10-21 08:30:00'),
(1, 1, 'ORD1002', 25000000.00, N'Đơn hàng máy in nhiệt - Đã đổi lại QR và thu đủ 25tr', 'CONFIRMED_ORDER', 'PAID', '2026-10-21 08:45:00'),
(1, 1, 'ORD1003', 15000000.00, N'Đơn hàng ngăn kéo đựng tiền - Mới thu 10tr, còn thiếu 5tr', 'CONFIRMED_ORDER', 'PARTIALLY_PAID', '2026-10-21 09:00:00'),
(1, 1, 'ORD1004', 10000000.00, N'Đơn hàng máy quét mã vạch - Đã xuất QR 10tr, chờ khách chuyển', 'CONFIRMED_ORDER', 'UNPAID', '2026-10-21 09:10:00'),
(1, 1, 'ORD1005', 10000000.00, N'Đơn hàng giấy in hóa đơn - Đơn hợp lệ nhưng CHƯA phát hành QR', 'CONFIRMED_ORDER', 'UNPAID', '2026-10-21 09:20:00'),
(1, 1, 'ORD1006',  8000000.00, N'Đơn hàng khách báo hủy - Dùng để test chặn phân bổ nhầm vào đơn hủy', 'CANCELLED_ORDER', 'UNPAID', '2026-10-21 09:25:00');

-- 7. NẠP BẢNG payment_requests
-- Tổng các QR đang ACTIVE hoặc FULFILLED = 40tr + 25tr + 15tr + 10tr = 90.000.000 VNĐ
-- Có kèm 1 bản ghi QR cũ của ORD1002 ở trạng thái REVOKED (20.000.000 VNĐ) để chứng minh không bị cộng trùng!
INSERT INTO dbo.payment_requests (order_id, request_code, expected_amount, qr_url, status, expires_at, created_at) VALUES
(1, 'REQ_ORD1001_V1',     40000000.00, 'https://img.vietqr.io/image/970422-0888999777-compact2.png?amount=40000000&addInfo=TT%20ORD1001', 'FULFILLED', '2026-10-24 22:00:00', '2026-10-21 08:31:00'),
(2, 'REQ_ORD1002_V1_OLD', 20000000.00, 'https://img.vietqr.io/image/970422-0888999777-compact2.png?amount=20000000&addInfo=TT%20ORD1002', 'REVOKED',   '2026-10-24 22:00:00', '2026-10-21 08:46:00'),
(2, 'REQ_ORD1002_V2_NEW', 25000000.00, 'https://img.vietqr.io/image/970422-0888999777-compact2.png?amount=25000000&addInfo=TT%20ORD1002', 'FULFILLED', '2026-10-24 22:00:00', '2026-10-21 08:50:00'),
(3, 'REQ_ORD1003_V1',     15000000.00, 'https://img.vietqr.io/image/970422-0888999777-compact2.png?amount=15000000&addInfo=TT%20ORD1003', 'ACTIVE',    '2026-10-24 22:00:00', '2026-10-21 09:01:00'),
(4, 'REQ_ORD1004_V1',     10000000.00, 'https://img.vietqr.io/image/970422-0888999777-compact2.png?amount=10000000&addInfo=TT%20ORD1004', 'ACTIVE',    '2026-10-24 22:00:00', '2026-10-21 09:11:00');

-- 8. NẠP BẢNG bank_transactions
-- Tổng tiền ngân hàng đã ghi nhận = 80.000.000 VNĐ (Gồm 75.000.000 VNĐ đã phân bổ + 5.000.000 VNĐ tiền treo UNMATCHED)
INSERT INTO dbo.bank_transactions (merchant_id, reference_code, amount, allocated_amount, unallocated_amount, transfer_content, sender_account, match_status, created_at) VALUES
(0, 'FT262910001', 40000000.00, 40000000.00,       0.00, N'TT ORD1001', '0123456789', 'FULLY_ALLOCATED', '2026-10-21 09:00:00'),
(0, 'FT262910002', 25000000.00, 25000000.00,       0.00, N'TT ORD1002', '0987654321', 'FULLY_ALLOCATED', '2026-10-21 09:15:00'),
(0, 'FT262910003', 10000000.00, 10000000.00,       0.00, N'TT ORD1003', '0911222333', 'FULLY_ALLOCATED', '2026-10-21 09:30:00'),
(0, 'FT262910004',  5000000.00,        0.00, 5000000.00, N'TT ORD9999 KHACH GHI SAI MA DON', '0944555666', 'UNMATCHED', '2026-10-21 09:45:00');

-- 9. NẠP BẢNG payment_allocations (Sổ cái Append-Only với chuỗi băm SHA-256 nối tiếp chuẩn xác)
-- Công thức băm chuẩn: SHA256(prev_hash | id | bank_transaction_id | payment_request_id | order_id | entry_type | allocated_amount | reversal_of_id | created_at)
INSERT INTO dbo.payment_allocations (bank_transaction_id, payment_request_id, order_id, entry_type, allocated_amount, reversal_of_id, allocation_mode, prev_hash, record_hash, created_at) VALUES
(1, 1, 1, 'ALLOCATION', 40000000.00, NULL, 'AUTO', 
 'GENESIS_00000000000000000000000000000000000000000000000000000000', 
 'a063a4638c1fa6bf67c62466d57c4902132e5a3b0dffe4d1bf37e402c0c4cffc', 
 '2026-10-21 09:00:00'),

(2, 3, 2, 'ALLOCATION', 25000000.00, NULL, 'AUTO', 
 'a063a4638c1fa6bf67c62466d57c4902132e5a3b0dffe4d1bf37e402c0c4cffc', 
 '23017f62b38a47dfc9a12ea8ae746a33a31ec48071a48c472c7143b063172dd7', 
 '2026-10-21 09:15:00'),

(3, 4, 3, 'ALLOCATION', 10000000.00, NULL, 'AUTO', 
 '23017f62b38a47dfc9a12ea8ae746a33a31ec48071a48c472c7143b063172dd7', 
 'dfa9e2ac5cc708b105fb098e0993074ac25523a4897a4e884c5438f20b4dd947', 
 '2026-10-21 09:30:00');

-- 10. NẠP BẢNG decisions (Lịch sử quyết định ngoại lệ mẫu kèm bằng chứng WebAuthn)
INSERT INTO dbo.decisions (order_id, bank_transaction_id, reviewer_id, decision_type, reason, challenge_used, assertion_signature, biometric_verified, review_date) VALUES
(3, 3, 2, 'REQUEST_INFO', N'Đơn ORD1003 khách mới chuyển 10.000.000đ, còn thiếu 5.000.000đ. Yêu cầu thu ngân nhắc khách quét lại QR để chuyển bù.', 'CHALLENGE_DEMO_001', 'SIG_WEBAUTHN_DEMO_001', 1, '2026-10-21 09:35:00');

COMMIT TRANSACTION;
GO