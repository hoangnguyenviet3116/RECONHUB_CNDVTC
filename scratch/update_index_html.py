# -*- coding: utf-8 -*-
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    <!-- HỘP THOẠI: XEM TÓM TẮT CA -->"""

replacement = """    <!-- HỘP THOẠI XÁC NHẬN ĐÓNG CA THỦ CÔNG -->
    <div class="modal fade" id="confirmCloseShiftModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered" style="max-width: 440px;">
            <div class="modal-content border-0 shadow-lg" style="border-radius: 18px;">
                <div class="modal-header border-bottom pb-2 pt-3 px-4">
                    <div class="d-flex align-items-center gap-2">
                        <span class="fp-brand-mark" style="width:32px;height:32px;background:#fff1f2;color:#e11d48;border:1px solid #fecdd3;">
                            <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                            </svg>
                        </span>
                        <h3 class="h6 fw-bold mb-0 text-danger">Xác Nhận Đóng Ca Làm Việc</h3>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Đóng"></button>
                </div>
                <div class="modal-body px-4 pb-4 pt-3">
                    <p class="small text-secondary mb-2">
                        Bạn đang chuẩn bị đóng ca bán hàng:
                    </p>
                    <div class="p-2 px-3 rounded-3 bg-light border mb-3">
                        <strong class="d-block text-dark" id="modal-close-shift-name">Ca làm việc</strong>
                        <span class="text-secondary small">Mã ca: #<span id="modal-close-shift-id">-</span></span>
                    </div>
                    <div class="alert alert-warning py-2 px-3 small mb-3 border-0">
                        <strong>Lưu ý:</strong> Sau khi đóng ca, Quầy thu ngân sẽ <strong>ngay lập tức bị vô hiệu hóa</strong> việc tạo hóa đơn mới cho ca này. Các hóa đơn và giao dịch đã tạo trước đó vẫn được bảo toàn cho công tác đối soát.
                    </div>
                    <div id="close-shift-error" class="alert alert-danger py-2 px-3 small d-none" role="alert"></div>
                    <div class="d-flex justify-content-end gap-2 mt-3">
                        <button type="button" class="btn-fp-outline" data-bs-dismiss="modal">Hủy bỏ</button>
                        <button type="button" class="btn-fp-danger py-2 px-3" id="btn-confirm-close-shift">
                            Xác nhận đóng ca
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- HỘP THOẠI: XEM TÓM TẮT CA -->"""

assert target in c, "target not found in index.html"
c = c.replace(target, replacement, 1)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated frontend/index.html successfully")
