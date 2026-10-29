# -*- coding: utf-8 -*-

new_html = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cổng Thanh Toán Ngân Hàng — VietQR ReconHub</title>

    <!-- Google Fonts: Be Vietnam Pro & Inter -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- Bootstrap 5.3 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="css/styles.css" rel="stylesheet">
</head>
<body>

    <!-- Thanh điều hướng ứng dụng -->
    <div id="app-navbar"></div>

    <main class="py-4">
        <div class="container shift-page-wrapper">

            <!-- ===============================================================
                 TIÊU ĐỀ TRANG: MÔI TRƯỜNG MÔ PHỎNG / CỔNG THANH TOÁN
                 =============================================================== -->
            <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4" data-gsap="card">
                <div>
                    <div class="shift-eyebrow">MÔI TRƯỜNG MÔ PHỎNG</div>
                    <h1 class="shift-main-title mb-1">Cổng thanh toán</h1>
                    <p class="shift-sub-title mb-0">Mô phỏng giao dịch ngân hàng và kiểm tra các tình huống thanh toán.</p>
                </div>
                <div>
                    <span class="pos-status-pill pos-status-unpaid">Chế độ thử nghiệm</span>
                </div>
            </div>

            <!-- ===============================================================
                 KHỐI TRÊN: FORM TẠO LỆNH CHUYỂN TIỀN & BIÊN LAI GIAO DỊCH
                 =============================================================== -->
            <div class="row g-4 align-items-stretch">

                <!-- Cột trái (6/12): Tạo lệnh chuyển tiền -->
                <div class="col-12 col-lg-6" data-gsap="card">
                    <section class="shift-create-card h-100">
                        <!-- Header thẻ -->
                        <div class="shift-create-card-header mb-3">
                            <div class="shift-create-icon-badge">
                                <svg class="hi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"/>
                                </svg>
                            </div>
                            <div>
                                <h2 class="h6 fw-bold mb-0 text-dark" style="font-size: 1.05rem;">Tạo lệnh chuyển tiền</h2>
                                <p class="text-secondary small mb-0">Thông tin người nhận đã được xác thực</p>
                            </div>
                        </div>

                        <!-- Khung thông tin tài khoản người nhận (Beneficiary Account Box) -->
                        <div class="sim-bank-account-box mb-3">
                            <div class="d-flex align-items-center justify-content-between">
                                <div class="d-flex align-items-center gap-3">
                                    <div class="sim-bank-avatar">
                                        MB
                                    </div>
                                    <div>
                                        <div class="sim-bank-label">Chuyển đến</div>
                                        <div class="sim-bank-name">CTY TNHH RECONHUB RETAIL</div>
                                        <div class="sim-bank-sub">MB Bank &nbsp;•&nbsp; 0888 999 777</div>
                                    </div>
                                </div>
                                <div class="sim-bank-check-icon">
                                    <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="m4.5 12.75 6 6 9-13.5"/>
                                    </svg>
                                </div>
                            </div>
                        </div>

                        <!-- Form nhập liệu -->
                        <form id="mock-bank-form" novalidate>
                            <!-- 1. Chọn nhanh hóa đơn -->
                            <div class="mb-3">
                                <label for="sim-order-select" class="shift-input-label">Chọn nhanh hóa đơn</label>
                                <select id="sim-order-select" class="form-select shift-input">
                                    <option value="">-- Tự nhập thông tin chuyển khoản --</option>
                                </select>
                            </div>

                            <!-- 2. Hàng: Số tiền & Nội dung chuyển khoản -->
                            <div class="row g-3 mb-3">
                                <div class="col-12 col-sm-6">
                                    <label for="sim-amount" class="shift-input-label">Số tiền</label>
                                    <div class="input-group">
                                        <input type="number" id="sim-amount" class="form-control shift-input font-numeric fw-bold" required min="1000" step="1000" value="250000">
                                        <span class="input-group-text shift-input-addon">đ</span>
                                    </div>
                                </div>
                                <div class="col-12 col-sm-6">
                                    <label for="sim-transfer-content" class="shift-input-label">Nội dung chuyển khoản</label>
                                    <input type="text" id="sim-transfer-content" class="form-control shift-input fw-semibold" required value="TT ORD1003">
                                </div>
                            </div>

                            <!-- 3. Tình huống mô phỏng -->
                            <div class="mb-3">
                                <label for="sim-scenario-select" class="shift-input-label">Tình huống mô phỏng</label>
                                <select id="sim-scenario-select" class="form-select shift-input">
                                    <option value="TC02_EXACT" selected>Giao dịch thành công (Đúng &amp; đủ tiền)</option>
                                    <option value="TC03_PARTIAL">Chuyển thiếu tiền (Trả trước 1 phần)</option>
                                    <option value="TC04_OVERPAID">Chuyển dư tiền (Tách riêng tiền thừa)</option>
                                    <option value="TC05_WRONG_CODE">Sai nội dung (Quên ghi mã đơn)</option>
                                </select>
                            </div>

                            <!-- 4. Mã giao dịch & Chế độ gửi (Tùy chọn nâng cao) -->
                            <div class="row g-2 mb-3">
                                <div class="col-7">
                                    <div class="d-flex justify-content-between align-items-center mb-1">
                                        <label for="sim-reference-code" class="shift-input-label mb-0" style="font-size:0.75rem;">Mã giao dịch</label>
                                        <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" id="btn-gen-ref-code" style="font-size: 0.72rem;">
                                            ↻ Đổi mã
                                        </button>
                                    </div>
                                    <input type="text" id="sim-reference-code" class="form-control shift-input font-numeric" style="height: 38px; font-size: 0.82rem;" required value="FT2629488101">
                                </div>
                                <div class="col-5">
                                    <label for="sim-test-mode" class="shift-input-label mb-1" style="font-size:0.75rem;">Bảo mật / Chữ ký</label>
                                    <select id="sim-test-mode" class="form-select shift-input" style="height: 38px; font-size: 0.82rem;">
                                        <option value="STANDARD">HMAC hợp lệ</option>
                                        <option value="INVALID_HMAC">Sai chữ ký số</option>
                                        <option value="CONCURRENT_DUPLICATE">Gửi trùng 2 lần</option>
                                        <option value="REPLAY_ATTACK">Tấn công phát lại</option>
                                    </select>
                                </div>
                            </div>

                            <div id="sim-form-error" class="alert alert-danger py-2 px-3 small d-none mb-3" role="alert"></div>

                            <button type="submit" class="btn-pos-create w-100 py-3" id="btn-trigger-transfer">
                                <span>→ Xác nhận chuyển khoản</span>
                            </button>

                            <div class="text-center text-secondary small mt-3" style="font-size: 0.78rem;">
                                <svg class="hi-icon hi-icon-sm text-secondary me-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px;">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
                                </svg>
                                <span>Không phát sinh giao dịch tiền thật trong chế độ thử nghiệm.</span>
                            </div>
                        </form>
                    </section>
                </div>

                <!-- Cột phải (6/12): Biên lai giao dịch -->
                <div class="col-12 col-lg-6" data-gsap="card">
                    <section class="sim-receipt-card h-100">
                        <div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom">
                            <h2 class="h6 fw-bold mb-0 text-dark">Biên lai giao dịch</h2>
                            <span class="pos-status-pill pos-status-unpaid" id="inspector-http-status">Chờ giao dịch</span>
                        </div>

                        <div id="inspector-friendly-box" class="flex-grow-1 d-flex flex-column justify-content-center">
                            <div class="sim-empty-receipt">
                                <div class="sim-empty-icon">
                                    <svg class="hi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" style="width: 28px; height: 28px;">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"/>
                                    </svg>
                                </div>
                                <div class="fw-bold text-dark mb-1" style="font-size: 1rem;">Biên lai sẽ xuất hiện tại đây</div>
                                <p class="text-secondary small mb-0">Hoàn tất lệnh chuyển tiền để xem kết quả giao dịch.</p>
                            </div>
                        </div>
                    </section>
                </div>

            </div>

            <!-- ===============================================================
                 KHỐI DƯỚI: BẢNG LỊCH SỬ GIAO DỊCH TOÀN BỘ (FULL WIDTH)
                 =============================================================== -->
            <div class="row mt-4" data-gsap="card">
                <div class="col-12">
                    <section class="shift-create-card">
                        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 pb-3 mb-3 border-bottom">
                            <div>
                                <h2 class="h5 fw-bold mb-1 text-dark">Lịch sử giao dịch</h2>
                                <p class="text-secondary small mb-0">Các khoản chuyển vào cửa hàng, mới nhất trước</p>
                            </div>
                            <button type="button" class="btn-shift-refresh" id="btn-refresh-bank-tx" title="Làm mới">
                                <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"/>
                                </svg>
                                <span>Làm mới</span>
                            </button>
                        </div>

                        <div class="table-responsive">
                            <table class="pos-modern-table">
                                <thead>
                                    <tr>
                                        <th>THỜI GIAN</th>
                                        <th>MÃ GIAO DỊCH</th>
                                        <th>NỘI DUNG</th>
                                        <th>SỐ TIỀN</th>
                                        <th class="text-end">KẾT QUẢ ĐỐI SOÁT</th>
                                    </tr>
                                </thead>
                                <tbody id="sim-bank-tx-tbody">
                                    <tr>
                                        <td colspan="5" class="text-center py-5 text-secondary">
                                            Đang tải lịch sử giao dịch...
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>
                </div>
            </div>

        </div>
    </main>

    <div id="app-footer"></div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="js/api.js"></script>
    <script src="js/tts_speaker.js"></script>
    <script src="js/bank_simulator.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            renderNavbar("simulator");
            renderFooter();
            initPageAnimations();
            initBankSimulatorPage();
        });
    </script>
</body>
</html>
"""

with open("frontend/bank-simulator.html", "w", encoding="utf-8") as f:
    f.write(new_html)

print("Updated frontend/bank-simulator.html successfully.")
