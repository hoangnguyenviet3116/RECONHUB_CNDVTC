--Script khởi tạo 9 bảng chuẩn trên Microsoft SQL Server (Append-Only Ledger)

SET NOCOUNT ON;
GO

-- -----------------------------------------------------------------------------------
-- 1. XÓA CÁC BẢNG CŨ THEO THỨ TỰ NGƯỢC KHÓA NGOẠI (ĐỂ CHẠY LẠI SẠCH SẼ KHÔNG LỖI)
-- -----------------------------------------------------------------------------------
IF OBJECT_ID('dbo.decisions', 'U') IS NOT NULL DROP TABLE dbo.decisions;
IF OBJECT_ID('dbo.payment_allocations', 'U') IS NOT NULL DROP TABLE dbo.payment_allocations;
IF OBJECT_ID('dbo.bank_transactions', 'U') IS NOT NULL DROP TABLE dbo.bank_transactions;
IF OBJECT_ID('dbo.payment_requests', 'U') IS NOT NULL DROP TABLE dbo.payment_requests;
IF OBJECT_ID('dbo.orders', 'U') IS NOT NULL DROP TABLE dbo.orders;
IF OBJECT_ID('dbo.shifts', 'U') IS NOT NULL DROP TABLE dbo.shifts;
IF OBJECT_ID('dbo.merchant_users', 'U') IS NOT NULL DROP TABLE dbo.merchant_users;
IF OBJECT_ID('dbo.merchants', 'U') IS NOT NULL DROP TABLE dbo.merchants;
IF OBJECT_ID('dbo.users', 'U') IS NOT NULL DROP TABLE dbo.users;
GO

-- -----------------------------------------------------------------------------------
-- 2. KHỞI TẠO 9 BẢNG DỮ LIỆU CHUẨN MVP
-- -----------------------------------------------------------------------------------

-- BẢNG 1: users (Lưu tài khoản người dùng, email và thông tin khóa xác thực WebAuthn)
CREATE TABLE dbo.users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    full_name NVARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    webauthn_credential_id NVARCHAR(255) NULL,
    webauthn_public_key NVARCHAR(MAX) NULL,
    current_challenge NVARCHAR(255) NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_users_email UNIQUE (email)
);

-- BẢNG 2: merchants (Lưu thông tin hộ kinh doanh/cửa hàng, ngân hàng nhận VietQR & khóa HMAC)
CREATE TABLE dbo.merchants (
    id INT IDENTITY(1,1) PRIMARY KEY,
    merchant_code VARCHAR(30) NOT NULL,
    name NVARCHAR(150) NOT NULL,
    bank_bin VARCHAR(20) NOT NULL,
    account_no VARCHAR(50) NOT NULL,
    webhook_secret VARCHAR(100) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_merchants_code UNIQUE (merchant_code)
);

-- BẢNG 3: merchant_users (Lưu phân quyền nhân sự thuộc từng cửa hàng: CASHIER, REVIEWER, OWNER)
CREATE TABLE dbo.merchant_users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    merchant_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    CONSTRAINT UQ_merchant_users_pair UNIQUE (user_id, merchant_id),
    CONSTRAINT CK_merchant_users_role CHECK (role IN ('CASHIER', 'REVIEWER', 'OWNER')),
    CONSTRAINT FK_merchant_users_users FOREIGN KEY (user_id) REFERENCES dbo.users(id),
    CONSTRAINT FK_merchant_users_merchants FOREIGN KEY (merchant_id) REFERENCES dbo.merchants(id)
);

-- BẢNG 4: shifts (Quản lý ca làm việc của cửa hàng và mục tiêu doanh thu tham khảo)
CREATE TABLE dbo.shifts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    merchant_id INT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    target_revenue DECIMAL(18,2) NOT NULL,
    start_time DATETIME2 NOT NULL,
    end_time DATETIME2 NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    CONSTRAINT CK_shifts_target_revenue CHECK (target_revenue > 0),
    CONSTRAINT CK_shifts_time_valid CHECK (end_time > start_time),
    CONSTRAINT CK_shifts_status CHECK (status IN ('DRAFT', 'OPEN', 'CLOSED', 'CANCELLED')),
    CONSTRAINT FK_shifts_merchants FOREIGN KEY (merchant_id) REFERENCES dbo.merchants(id)
);

-- BẢNG 5: orders (Lưu đơn hàng phát sinh trong ca, tách biệt order_status và payment_status)
CREATE TABLE dbo.orders (
    id INT IDENTITY(1,1) PRIMARY KEY,
    shift_id INT NOT NULL,
    created_by INT NOT NULL,
    order_code VARCHAR(30) NOT NULL,
    total_amount DECIMAL(18,2) NOT NULL,
    customer_note NVARCHAR(255) NULL,
    order_status VARCHAR(30) NOT NULL DEFAULT 'CONFIRMED_ORDER',
    payment_status VARCHAR(30) NOT NULL DEFAULT 'UNPAID',
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_orders_total_amount CHECK (total_amount > 0),
    CONSTRAINT CK_orders_order_status CHECK (order_status IN ('DRAFT', 'CONFIRMED_ORDER', 'UNDER_REVIEW', 'CANCELLED_ORDER')),
    CONSTRAINT CK_orders_payment_status CHECK (payment_status IN ('UNPAID', 'PARTIALLY_PAID', 'PAID')),
    CONSTRAINT FK_orders_shifts FOREIGN KEY (shift_id) REFERENCES dbo.shifts(id),
    CONSTRAINT FK_orders_users FOREIGN KEY (created_by) REFERENCES dbo.users(id)
);

-- Chỉ mục duy nhất UNIQUE INDEX trên orders.order_code phục vụ khóa dòng WITH (UPDLOCK, ROWLOCK)
CREATE UNIQUE NONCLUSTERED INDEX UX_orders_order_code ON dbo.orders(order_code);

-- BẢNG 6: payment_requests (Lưu các yêu cầu thu mã VietQR động gắn với đơn hàng)
CREATE TABLE dbo.payment_requests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    order_id INT NOT NULL,
    request_code VARCHAR(40) NOT NULL,
    expected_amount DECIMAL(18,2) NOT NULL,
    qr_url NVARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    expires_at DATETIME2 NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_payment_requests_code UNIQUE (request_code),
    CONSTRAINT CK_payment_requests_amount CHECK (expected_amount > 0),
    CONSTRAINT CK_payment_requests_status CHECK (status IN ('ACTIVE', 'FULFILLED', 'EXPIRED', 'REVOKED')),
    CONSTRAINT FK_payment_requests_orders FOREIGN KEY (order_id) REFERENCES dbo.orders(id)
);

-- Filtered Unique Index: Đảm bảo mỗi đơn hàng chỉ có tối đa 01 bản ghi đang ACTIVE hoặc FULFILLED
CREATE UNIQUE NONCLUSTERED INDEX UX_payment_requests_one_active_per_order 
ON dbo.payment_requests(order_id) 
WHERE status IN ('ACTIVE', 'FULFILLED');

-- BẢNG 7: bank_transactions (Lưu độc lập toàn bộ giao dịch ngân hàng nhận từ Webhook)
CREATE TABLE dbo.bank_transactions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    merchant_id INT NOT NULL,
    reference_code VARCHAR(50) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    allocated_amount DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    unallocated_amount DECIMAL(18,2) NOT NULL,
    transfer_content NVARCHAR(255) NOT NULL,
    sender_account VARCHAR(50) NULL,
    match_status VARCHAR(30) NOT NULL DEFAULT 'UNMATCHED',
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_bank_tx_amount_positive CHECK (amount > 0),
    CONSTRAINT CK_bank_tx_balance_equation CHECK (
        allocated_amount >= 0 
        AND unallocated_amount >= 0 
        AND (allocated_amount + unallocated_amount = amount)
    ),
    CONSTRAINT CK_bank_tx_match_status CHECK (match_status IN ('UNMATCHED', 'PARTIALLY_ALLOCATED', 'FULLY_ALLOCATED', 'REJECTED_TX')),
    CONSTRAINT FK_bank_tx_merchants FOREIGN KEY (merchant_id) REFERENCES dbo.merchants(id)
);

-- Chỉ mục duy nhất UNIQUE INDEX trên bank_transactions.reference_code chống ghi trùng đồng thời
CREATE UNIQUE NONCLUSTERED INDEX UX_bank_transactions_reference_code ON dbo.bank_transactions(reference_code);

-- BẢNG 8: payment_allocations (Sổ cái chỉ ghi thêm Append-Only Ledger kèm chuỗi băm SHA-256)
CREATE TABLE dbo.payment_allocations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    bank_transaction_id INT NOT NULL,
    payment_request_id INT NOT NULL,
    order_id INT NOT NULL,
    entry_type VARCHAR(20) NOT NULL,
    allocated_amount DECIMAL(18,2) NOT NULL,
    reversal_of_id INT NULL,
    allocation_mode VARCHAR(20) NOT NULL DEFAULT 'AUTO',
    prev_hash VARCHAR(64) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_payment_allocations_entry_type CHECK (entry_type IN ('ALLOCATION', 'REVERSAL')),
    CONSTRAINT CK_payment_allocations_mode CHECK (allocation_mode IN ('AUTO', 'MANUAL', 'REVERSAL')),
    CONSTRAINT CK_payment_allocations_sign_rule CHECK (
        (entry_type = 'ALLOCATION' AND allocated_amount > 0 AND reversal_of_id IS NULL)
        OR (entry_type = 'REVERSAL' AND allocated_amount < 0 AND reversal_of_id IS NOT NULL)
    ),
    CONSTRAINT FK_allocations_bank_tx FOREIGN KEY (bank_transaction_id) REFERENCES dbo.bank_transactions(id),
    CONSTRAINT FK_allocations_requests FOREIGN KEY (payment_request_id) REFERENCES dbo.payment_requests(id),
    CONSTRAINT FK_allocations_orders FOREIGN KEY (order_id) REFERENCES dbo.orders(id),
    CONSTRAINT FK_allocations_reversal_self FOREIGN KEY (reversal_of_id) REFERENCES dbo.payment_allocations(id)
);

-- Filtered Unique Index: Mỗi bút toán ALLOCATION gốc chỉ được đảo (REVERSAL) tối đa 01 lần
CREATE UNIQUE NONCLUSTERED INDEX UX_payment_allocations_reversal_of_id 
ON dbo.payment_allocations(reversal_of_id) 
WHERE reversal_of_id IS NOT NULL;

-- BẢNG 9: decisions (Lưu lịch sử quyết định ngoại lệ, đảo bút toán kèm bằng chứng WebAuthn)
CREATE TABLE dbo.decisions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    order_id INT NULL,
    bank_transaction_id INT NULL,
    reviewer_id INT NOT NULL,
    decision_type VARCHAR(30) NOT NULL,
    reason NVARCHAR(500) NOT NULL,
    challenge_used NVARCHAR(255) NULL,
    assertion_signature NVARCHAR(MAX) NULL,
    biometric_verified BIT NOT NULL DEFAULT 0,
    review_date DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_decisions_type CHECK (decision_type IN ('APPROVE_MANUAL_MATCH', 'REVERSE_ALLOCATION', 'REQUEST_INFO', 'REJECT_TX')),
    CONSTRAINT CK_decisions_reason_not_empty CHECK (LEN(TRIM(reason)) > 0),
    CONSTRAINT FK_decisions_orders FOREIGN KEY (order_id) REFERENCES dbo.orders(id),
    CONSTRAINT FK_decisions_bank_tx FOREIGN KEY (bank_transaction_id) REFERENCES dbo.bank_transactions(id),
    CONSTRAINT FK_decisions_users FOREIGN KEY (reviewer_id) REFERENCES dbo.users(id)
);
GO