import sys

with open("frontend/reconciliation.html", "r", encoding="utf-8") as f:
    html_content = f.read()

html_norm = html_content.replace("\r\n", "\n")

target_modal_header = """                    <div>
                        <span class="fp-badge fp-badge-dark mb-1">Xử lý tiền chờ đối soát</span>
                        <h2 class="h5 fw-bold mb-0">Ghép Khoản Tiền Vào Hóa Đơn</h2>
                    </div>"""

replacement_modal_header = """                    <div>
                        <span class="fp-badge fp-badge-dark mb-1">Xử lý tiền chờ đối soát</span>
                        <h2 class="h5 fw-bold mb-0">Ghép tiền vào hóa đơn</h2>
                    </div>"""

assert target_modal_header in html_norm, "target_modal_header not found"
html_norm = html_norm.replace(target_modal_header, replacement_modal_header)

target_match_btn = """                        <div class="d-flex justify-content-end gap-2 mt-3">
                            <button type="button" class="btn-fp-outline" data-bs-dismiss="modal">Hủy</button>
                            <button type="submit" class="btn-fp-success" id="btn-confirm-match">
                                Xác nhận ghép vào đơn
                            </button>
                        </div>"""

replacement_match_btn = """                        <div class="d-flex justify-content-end gap-2 mt-3">
                            <button type="button" class="btn-fp-outline" data-bs-dismiss="modal">Hủy</button>
                            <button type="submit" class="btn-fp-success" id="btn-confirm-match">
                                Xác nhận
                            </button>
                        </div>"""

assert target_match_btn in html_norm, "target_match_btn not found"
html_norm = html_norm.replace(target_match_btn, replacement_match_btn)

# Add overpaymentModal after manualMatchModal
target_reverse_modal = """    <!-- =======================================================================
         HỘP THOẠI 2: ĐẢO / HỦY KHOẢN TIỀN ĐÃ GHÉP (KHI BẤM NÚT ĐẢO GIAO DỊCH)
         ======================================================================= -->"""

overpayment_modal_snippet = """    <!-- =======================================================================
         HỘP THOẠI: PHƯƠNG THỨC XỬ LÝ (KHI BẤM NÚT XỬ LÝ TRÊN GIAO DỊCH CHUYỂN THỪA)
         ======================================================================= -->
    <div class="modal fade" id="overpaymentModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content border-0 shadow-lg" style="border-radius: 18px;">
                <div class="modal-header border-bottom pb-3 pt-4 px-4">
                    <div>
                        <span class="fp-badge fp-badge-warning mb-1">Xử lý chênh lệch tiền thừa</span>
                        <h2 class="h5 fw-bold mb-0">Phương thức xử lý</h2>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Đóng"></button>
                </div>

                <div class="modal-body px-4 pb-4 pt-3">
                    <form id="form-overpayment" novalidate>
                        <input type="hidden" id="ovp-tx-id">
                        <input type="hidden" id="ovp-order-id">

                        <!-- Thông tin giao dịch chuyển thừa -->
                        <div class="p-3 rounded-3 bg-light border small mb-3">
                            <div class="d-flex justify-content-between py-1 border-bottom">
                                <span class="text-secondary">Mã giao dịch ngân hàng:</span>
                                <strong id="ovp-tx-code" class="font-numeric">—</strong>
                            </div>
                            <div class="d-flex justify-content-between py-1 border-bottom">
                                <span class="text-secondary">Mã hóa đơn:</span>
                                <strong id="ovp-order-code" class="text-dark font-numeric">—</strong>
                            </div>
                            <div class="d-flex justify-content-between py-1 border-bottom">
                                <span class="text-secondary">Số tiền giao dịch:</span>
                                <strong id="ovp-tx-amount" class="font-numeric text-dark">—</strong>
                            </div>
                            <div class="d-flex justify-content-between py-1 border-bottom">
                                <span class="text-secondary">Số tiền hóa đơn:</span>
                                <strong id="ovp-order-amount" class="font-numeric text-secondary">—</strong>
                            </div>
                            <div class="d-flex justify-content-between pt-1">
                                <span class="text-secondary">Số tiền chuyển thừa:</span>
                                <strong id="ovp-unallocated-amount" class="text-danger fs-6 font-numeric">—</strong>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label for="ovp-method-input" class="form-label small fw-semibold">Phương thức xử lý <span class="text-danger">*</span></label>
                            <textarea id="ovp-method-input" class="form-control" rows="3" required placeholder="Ghi rõ phương thức xử lý khoản tiền thừa (ví dụ: Đã hoàn tiền mặt cho khách, hoặc trừ vào đơn hàng sau...)..."></textarea>
                        </div>

                        <div class="mb-3">
                            <label for="ovp-security-mode" class="form-label small text-secondary mb-1">Xác thực phê duyệt</label>
                            <select id="ovp-security-mode" class="form-select form-select-sm">
                                <option value="WEBAUTHN_SIGN">Xác nhận bằng khóa bảo mật thiết bị (Vân tay / Mã PIN)</option>
                                <option value="BYPASS_WEBAUTHN_TEST">Thử nghiệm: Gửi yêu cầu không qua khóa bảo mật</option>
                            </select>
                        </div>

                        <div id="ovp-error-box" class="alert alert-danger py-2 px-3 small d-none" role="alert"></div>

                        <div class="d-flex justify-content-end gap-2 mt-3">
                            <button type="button" class="btn-fp-outline" data-bs-dismiss="modal">Hủy</button>
                            <button type="submit" class="btn-fp-success" id="btn-confirm-ovp">
                                Xác nhận
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>

""" + target_reverse_modal

assert target_reverse_modal in html_norm, "target_reverse_modal not found"
html_norm = html_norm.replace(target_reverse_modal, overpayment_modal_snippet)

if "\r\n" in html_content:
    html_norm = html_norm.replace("\n", "\r\n")

with open("frontend/reconciliation.html", "w", encoding="utf-8") as f:
    f.write(html_norm)

print("SUCCESS: frontend/reconciliation.html updated")
