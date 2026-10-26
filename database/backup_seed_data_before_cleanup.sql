-- =============================================================================
-- BẢN SAO LƯU DỮ LIỆU MẪU TRƯỚC KHI DỌN DẸP SẠCH PRODUCTION
-- Ngày tạo: 2026-10-24
-- Mục đích: Lưu trữ lại trạng thái dữ liệu mẫu cũ phục vụ tra cứu / đối soát
-- =============================================================================

-- 1. BẢNG users
-- ID 1: Nguyễn Việt Hoàng (Thu Ngân POS) - cashier@reconhub.vn
-- ID 2: Trần Thu Thảo (Kế Toán Đối Soát) - reviewer@reconhub.vn
-- ID 3: Lê Hồng Hạnh (Chủ Cửa Hàng) - owner@reconhub.vn

-- 2. BẢNG merchants
-- ID 1: MC_RECON_01 - VietQR ReconHub Flagship Store - Hà Nội

-- 3. BẢNG shifts (MẪU CŨ)
-- ID 1: 'Ca Kinh Doanh Chính - Ngày 24/10/2026' (120tr, OPEN)
-- ID 2: 'Ca Dự Phòng Ngày Mai - 25/10/2026' (80tr, DRAFT)

-- 4. BẢNG orders (MẪU CŨ)
-- ID 1: ORD1001 (40.000.000 VNĐ, PAID)
-- ID 2: ORD1002 (25.000.000 VNĐ, PAID)
-- ID 3: ORD1003 (15.000.000 VNĐ, PARTIALLY_PAID)
-- ID 4: ORD1004 (10.000.000 VNĐ, UNPAID)
-- ID 5: ORD1005 (10.000.000 VNĐ, UNPAID)
-- ID 6: ORD1006 (8.000.000 VNĐ, CANCELLED_ORDER)

-- 5. BẢNG payment_requests (MẪU CŨ)
-- ID 1: REQ_ORD1001_V1 (40tr, FULFILLED)
-- ID 2: REQ_ORD1002_V1_OLD (20tr, REVOKED)
-- ID 3: REQ_ORD1002_V2_NEW (25tr, FULFILLED)
-- ID 4: REQ_ORD1003_V1 (15tr, ACTIVE)
-- ID 5: REQ_ORD1004_V1 (10tr, ACTIVE)

-- 6. BẢNG bank_transactions (MẪU CŨ)
-- ID 1: FT262910001 (40.000.000 VNĐ, FULLY_ALLOCATED)
-- ID 2: FT262910002 (25.000.000 VNĐ, FULLY_ALLOCATED)
-- ID 3: FT262910003 (10.000.000 VNĐ, FULLY_ALLOCATED)
-- ID 4: FT262910004 (5.000.000 VNĐ, UNMATCHED)

-- 7. BẢNG payment_allocations (MẪU CŨ)
-- ID 1: 40tr vào ORD1001
-- ID 2: 25tr vào ORD1002
-- ID 3: 10tr vào ORD1003

-- 8. BẢNG decisions (MẪU CŨ)
-- ID 1: REQUEST_INFO cho ORD1003
