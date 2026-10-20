# 🏦 VIETQR RECONHUB — Nền tảng Quản lý Đơn hàng, Đối soát Dòng tiền Tự động & Sổ cái Chỉ Ghi Thêm Phát hiện Chỉnh sửa

> **Tên đề tài chính thức:** Thiết kế mô hình dịch vụ FinTech **VietQR ReconHub** hỗ trợ quản lý đơn hàng, đối soát dòng tiền tự động và minh bạch hóa thanh toán QR cho Hộ kinh doanh tại Việt Nam.  
> **Học phần:** Công nghệ Dịch vụ Tài chính (CNDVTC)  
> **Repository:** `RECONHUB_CNDVTC`  
> **Hạn nghiệm thu Giai đoạn 1 (Bài kiểm tra số 2):** Trước 20:00, Thứ Bảy ngày 24/10/2026.

---

## 📌 1. Giới thiệu tổng quan

**VietQR ReconHub** là nền tảng phần mềm dịch vụ (**B2B SaaS FinTech**) đóng vai trò là lớp trung gian điều phối yêu cầu thanh toán và đối soát dữ liệu dòng tiền giữa điểm bán hàng (POS) của hộ kinh doanh và dịch vụ ngân hàng mô phỏng (Mock Bank Service).

> ⚠️ **Giới hạn quan trọng của bản mô phỏng (Academic MVP Disclaimer):**  
> Hệ thống sử dụng dữ liệu mô phỏng phục vụ học tập, **không giữ tiền của cửa hàng, không kết nối ngân hàng thương mại thật và không phát sinh giao dịch chuyển tiền thật**. Việc hiển thị mã QR động hoặc trạng thái `PAID` / `FULFILLED` trong hệ thống không đồng nghĩa với việc đã có kết nối nhận tiền trực tiếp từ ngân hàng thương mại thực tế. Các cơ chế bảo mật (`HMAC-SHA256`, `Append-Only Hash Chain`, `WebAuthn`) là biện pháp giảm thiểu rủi ro kỹ thuật trong môi trường mô phỏng.

---

## 🔒 2. Mười một Nguyên tắc Kỹ thuật, Nghiệp vụ & Triển khai (Đồng bộ 100%)

1. **Nguyên tắc 1 (Kiến trúc) — HMAC ký và xác minh hoàn toàn ở Backend:** Giao diện `bank-simulator.html` chỉ gửi lệnh kích hoạt, không giữ `WEBHOOK_SECRET`. Dịch vụ `mock_bank_service` tại Server ký `HMAC-SHA256` và ReconHub Backend xác minh.
2. **Nguyên tắc 2 (Kiến trúc) — WebAuthn xác minh ở Backend (Tách biệt `create` vs `get`):** Không gửi cờ `biometric_verified = true` dạng boolean từ JS. Tách rõ Đăng ký khóa (`navigator.credentials.create()`) và Xác thực assertion (`navigator.credentials.get()`) kiểm tra `challenge`, `credential_id` và chữ ký tại Server.
3. **Nguyên tắc 3 (Kiến trúc) — Sổ cái chuỗi băm chỉ ghi thêm (`Append-Only Tamper-Evident Hash Chain`):** Bảng `payment_allocations` **tuyệt đối không dùng lệnh `UPDATE` sửa dòng cũ**. Sử dụng cột `entry_type` (`'ALLOCATION'` hoặc `'REVERSAL'`), `allocated_amount` (`+X` hoặc `-X`) và `reversal_of_id`. Khi đảo bút toán, chỉ `INSERT` thêm dòng mới `-X` nối tiếp vào cuối chuỗi để không bao giờ làm thay đổi dữ liệu dùng để tính hash của dòng cũ.
4. **Nguyên tắc 4 (Kiến trúc) — Dashboard lấy 100% KPI từ Backend:** Frontend chỉ hiển thị dữ liệu từ `GET /dashboard/summary`, không tự tính toán ở giao diện.
5. **Nguyên tắc 5 (Nghiệp vụ) — Định nghĩa `active_qr_request_total` không cộng trùng:** Khi tạo QR mới cho đơn, tự động chuyển QR cũ đang `ACTIVE` sang `REVOKED`. Chỉ cộng các bản ghi `ACTIVE` hoặc `FULFILLED` của đơn hợp lệ.
6. **Nguyên tắc 6 (Nghiệp vụ) — Quy tắc chuyển trạng thái 4 bảng & Điều kiện mở lại QR sau đảo bút toán:** Khi đảo bút toán làm tiền phân bổ ròng $< 	ext{expected\_amount}$, **chỉ mở lại `payment_requests.status` sang `ACTIVE`** nếu đơn còn hợp lệ VÀ QR chưa hết hạn (`expires_at > GETDATE()`) và chưa bị thu hồi; QR đã `EXPIRED` hoặc `REVOKED` tuyệt đối không tự động hồi sinh.
7. **Nguyên tắc 7 (Nghiệp vụ) — Kiểm thử khóa giao dịch thực tế trên SQL Server & Chặn phân bổ nhầm:** Thực thi khóa dòng qua Index (`WITH (UPDLOCK, ROWLOCK)` + `UNIQUE(reference_code)` + bắt `IntegrityError`) và kiểm thử thực tế trên SQL Server. Chặn tự động phân bổ vào đơn sai mã, **đơn đã hủy (`CANCELLED_ORDER`)** hoặc **đơn đã thu đủ (`PAID`)** — giữ nguyên toàn bộ tiền ở `bank_transactions.unallocated_amount` (`UNMATCHED`).
8. **Nguyên tắc 8 (Nghiệp vụ) — Loa thông báo `Web Speech TTS` phân biệt nội dung & chống đọc lặp:** Tách riêng lời đọc khi `PAID`, `PARTIALLY_PAID` và `Chuyển thừa`; lưu `lastAnnouncedState[order_code]` chống đọc lặp khi Polling.
9. **Nguyên tắc 9 (Nghiệp vụ) — Phân biệt Mã VietQR động & Ngân hàng thật:** Mã QR tạo theo chuẩn tương thích EMVCo / NAPAS 247 điền sẵn `bank_bin`, `account_no`, `expected_amount`, `TT ORDxxx`.
10. **Nguyên tắc 10 (Triển khai) — Tiêu chí Hoàn thành (Definition of Done):** Mỗi chức năng lõi phải có đủ Đầu vào + Xử lý Server/SQL Server + Kết quả mong đợi + Kiểm thử & Bằng chứng demo.
11. **Nguyên tắc 11 (Triển khai) — Thứ tự ưu tiên triển khai (20–24/10/2026):** (1) Đúng dữ liệu 9 bảng & công thức đối soát $
ightarrow$ (2) Luồng đơn – QR – Webhook HMAC – Phân bổ $
ightarrow$ (3) Khóa chống trùng SQL Server & chặn phân bổ nhầm $
ightarrow$ (4) Sổ cái `Append-Only Hash Chain` $
ightarrow$ (5) `WebAuthn`, `TTS` & biểu đồ Dashboard.

---

## 🗄️ 3. Mô hình 9 Bảng Cơ sở dữ liệu Microsoft SQL Server

1. **`users`**: Tài khoản người dùng (`id`, `full_name`, `email`, `password_hash`, `webauthn_credential_id`, `webauthn_public_key`, `current_challenge`).
2. **`merchants`**: Cửa hàng (`id`, `merchant_code`, `name`, `bank_bin`, `account_no`, `webhook_secret`).
3. **`merchant_users`**: Phân quyền người dùng theo cửa hàng (`user_id`, `merchant_id`, `role`: `CASHIER` | `REVIEWER` | `OWNER`).
4. **`shifts`**: Ca bán hàng (`id`, `merchant_id`, `name`, `target_revenue` *[chỉ làm KPI tham khảo]*, `status`: `DRAFT` | `OPEN` | `CLOSED` | `CANCELLED`).
5. **`orders`**: Đơn hàng (`id`, `shift_id`, `order_code` [UNIQUE INDEX], `total_amount`, `order_status`: `DRAFT` | `CONFIRMED_ORDER` | `UNDER_REVIEW` | `CANCELLED_ORDER`; `payment_status`: `UNPAID` | `PARTIALLY_PAID` | `PAID`).
6. **`payment_requests`**: Yêu cầu thu mã VietQR động (`id`, `order_id`, `request_code` [UNIQUE], `expected_amount`, `qr_url`, `status`: `ACTIVE` | `FULFILLED` | `EXPIRED` | `REVOKED`, `expires_at`).
7. **`bank_transactions`**: Giao dịch ngân hàng độc lập (`id`, `merchant_id`, `reference_code` [UNIQUE INDEX], `amount`, `allocated_amount`, `unallocated_amount`, `transfer_content`, `match_status`: `UNMATCHED` | `PARTIALLY_ALLOCATED` | `FULLY_ALLOCATED` | `REJECTED_TX`).
8. **`payment_allocations`**: **Sổ cái chỉ ghi thêm (`Append-Only Ledger`)** (`id`, `bank_transaction_id`, `payment_request_id`, `order_id`, `entry_type`: `'ALLOCATION'` | `'REVERSAL'`, `allocated_amount` [`+X` / `-X`], `reversal_of_id` [UNIQUE FK NULL], `allocation_mode`: `'AUTO'` | `'MANUAL'`, `prev_hash`, `record_hash`, `created_at`).
9. **`decisions`**: Lịch sử quyết định xét duyệt ngoại lệ có xác thực sinh trắc học (`id`, `order_id`, `bank_transaction_id`, `reviewer_id`, `decision_type`, `reason`, `challenge_used`, `assertion_signature`, `biometric_verified`).

---

## 🧮 4. Công thức Đối soát Tài chính Chuẩn hóa

Lấy **Tổng giá trị đơn hàng hợp lệ (`valid_order_total = 100 triệu`)** làm cơ sở gốc (không dùng `target_revenue`):
- **Chưa phát hành QR (`unissued_qr_amount`):** `100 triệu − 90 triệu = 10 triệu đồng`
- **Đã phát hành QR nhưng chưa thu đủ (`pending_qr_collection`):** `90 triệu − 75 triệu = 15 triệu đồng`
- **Tổng còn phải thu của đơn hợp lệ (`remaining_receivable`):** `100 triệu − 75 triệu = 25 triệu đồng`
- **Tiền ngân hàng chưa phân bổ (`unallocated_bank_tx_total`):** `5 triệu đồng`
