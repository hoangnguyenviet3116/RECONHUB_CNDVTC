import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Update frontend/pos.html
with open('frontend/pos.html', 'r', encoding='utf-8') as f:
    pos_html = f.read()

pos_html_norm = pos_html.replace('\r\n', '\n')

target_html = """                    <div class="p-3 rounded-3 bg-light border text-start small mb-3">
                        <div class="d-flex justify-content-between py-1 border-bottom">
                            <span class="text-secondary">Mã hóa đơn:</span>
                            <strong id="modal-qr-order-code">ORD1003</strong>
                        </div>
                        <div class="d-flex justify-content-between py-1 border-bottom">
                            <span class="text-secondary">Số tiền:</span>
                            <strong class="text-primary fs-6 font-numeric" id="modal-qr-expected-amount">15.000.000 ₫</strong>
                        </div>"""

replacement_html = """                    <div class="p-3 rounded-3 bg-light border text-start small mb-3">
                        <div class="d-flex justify-content-between py-1 border-bottom">
                            <span class="text-secondary">Mã hóa đơn:</span>
                            <strong id="modal-qr-order-code">ORD1003</strong>
                        </div>
                        <div class="d-flex justify-content-between py-1 border-bottom d-none" id="modal-qr-total-row">
                            <span class="text-secondary">Tổng đơn hàng:</span>
                            <strong class="text-secondary font-numeric" id="modal-qr-total-amount">0 ₫</strong>
                        </div>
                        <div class="d-flex justify-content-between py-1 border-bottom d-none" id="modal-qr-paid-amount-row">
                            <span class="text-secondary">Đã thanh toán trước:</span>
                            <strong class="text-success font-numeric" id="modal-qr-paid-amount">0 ₫</strong>
                        </div>
                        <div class="d-flex justify-content-between py-1 border-bottom">
                            <span class="text-secondary" id="modal-qr-amount-label">Số tiền:</span>
                            <strong class="text-primary fs-6 font-numeric" id="modal-qr-expected-amount">15.000.000 ₫</strong>
                        </div>"""

assert target_html in pos_html_norm, "Target HTML not found"
pos_html_norm = pos_html_norm.replace(target_html, replacement_html)

if '\r\n' in pos_html:
    pos_html_norm = pos_html_norm.replace('\n', '\r\n')

with open('frontend/pos.html', 'w', encoding='utf-8') as f:
    f.write(pos_html_norm)

print("SUCCESS: frontend/pos.html updated")

# 2. Update frontend/js/pos.js
with open('frontend/js/pos.js', 'r', encoding='utf-8') as f:
    pos_js = f.read()

pos_js_norm = pos_js.replace('\r\n', '\n')

target_modal_js = """async function openOrderQrModal(orderId, shouldIssueIfMissing = true) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    currentSelectedOrderForQr = order;
    const existingQr = order.qr_request || order.active_payment_request;

    if (shouldIssueIfMissing && (!existingQr || existingQr.status !== "ACTIVE")) {
        await issueDynamicVietQr(order.id, false);
    } else {
        displayQrInModal(order, existingQr);
    }
}

async function issueDynamicVietQr(orderId, isReissue = false) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    const remainingAmount = Math.max(0, Number(order.total_amount || 0) - Number(order.net_paid_amount || 0));
    const expected = remainingAmount > 0 ? remainingAmount : order.total_amount;

    try {
        const qrResp = await apiRequest("/payment-requests", {
            method: "POST",
            body: JSON.stringify({
                order_id: orderId,
                expected_amount: expected
            })
        });
        await loadPosOrders(false);
        const updatedOrder = posOrdersCache.find((o) => Number(o.id) === Number(orderId)) || order;
        displayQrInModal(updatedOrder, qrResp);
    } catch (error) {
        if (error.isNetworkError) {
            const store = getDemoStore();
            const target = store.orders.find((o) => Number(o.id) === Number(orderId));
            const simulatedQr = {
                request_code: `REQ-${order.order_code}-${Math.floor(10 + Math.random() * 89)}`,
                expected_amount: expected,
                status: "ACTIVE",
                qr_url: buildEmvcoVietQrUrl(order.order_code, expected),
                expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString()
            };
            if (target) {
                target.qr_request = simulatedQr;
                saveDemoStore(store);
                posOrdersCache = store.orders;
            }
            order.qr_request = simulatedQr;
            renderPosOrdersTable(posOrdersCache);
            displayQrInModal(order, simulatedQr);
        } else {
            showToast(error.message || "Không thể xuất mã QR.", "danger");
            return;
        }
    }

    showToast(
        isReissue ? `Đã đổi mã QR mới cho đơn ${order.order_code}` : `Đã tạo mã QR cho đơn ${order.order_code}`,
        "success"
    );
}

function displayQrInModal(order, qrData) {
    if (!order) return;
    currentSelectedOrderForQr = order;

    const isPaid = String(order.payment_status || "").toUpperCase() === "PAID";
    const totalAmount = Number(order.total_amount || 0);
    const paidAmount = Number(order.net_paid_amount ?? order.allocated_amount ?? totalAmount);

    const expectedAmount = isPaid
        ? (paidAmount > 0 ? paidAmount : totalAmount)
        : (qrData?.expected_amount ??
           Math.max(0, totalAmount - Number(order.net_paid_amount || 0)) ??
           totalAmount);

    const qrUrl = qrData?.qr_url || buildEmvcoVietQrUrl(order.order_code, expectedAmount);

    const badgeEl = document.getElementById("modal-qr-status-badge");
    const titleEl = document.getElementById("modal-qr-title");
    const qrFrameBox = document.getElementById("modal-qr-frame-box");
    const actionsEl = document.getElementById("modal-qr-actions");
    const paidTimeRow = document.getElementById("modal-qr-paid-time-row");
    const paidTimeEl = document.getElementById("modal-qr-paid-time");

    if (badgeEl) {
        badgeEl.className = `fp-badge ${isPaid ? "fp-badge-success" : "fp-badge-dark"} mb-1`;
        badgeEl.textContent = isPaid ? "✓ Đã thanh toán đủ" : "Mã QR đang hoạt động";
    }

    if (titleEl) {
        titleEl.textContent = isPaid ? "Biên Lai Thanh Toán" : "Quét Mã VietQR Thanh Toán";
    }

    // Nếu đã thanh toán (Xem biên lai): Ẩn ảnh QR và ẩn 2 nút hành động, chỉ hiện 4 dòng thông tin biên lai
    if (qrFrameBox) {
        qrFrameBox.classList.toggle("d-none", isPaid);
    }
    if (actionsEl) {
        actionsEl.classList.toggle("d-none", isPaid);
    }
    if (paidTimeRow) {
        paidTimeRow.classList.toggle("d-none", !isPaid);
    }

    if (paidTimeEl && isPaid) {
        const txTime =
            order.paid_at ||
            order.last_payment_at ||
            qrData?.created_at ||
            order.created_at;
        paidTimeEl.textContent = formatDateTime(txTime);
    }

    const imgEl = document.getElementById("modal-qr-image");
    const ordCodeEl = document.getElementById("modal-qr-order-code");
    const amountEl = document.getElementById("modal-qr-expected-amount");
    const contentEl = document.getElementById("modal-qr-transfer-content");
    const simLinkEl = document.getElementById("modal-link-simulator");

    if (imgEl && !isPaid) imgEl.src = qrUrl;
    if (ordCodeEl) ordCodeEl.textContent = order.order_code;
    if (amountEl) amountEl.textContent = formatVND(expectedAmount);
    if (contentEl) {
        contentEl.textContent = order.last_transfer_content || `TT ${order.order_code}`;
    }

    if (simLinkEl) {
        const currentShift = document.getElementById("pos-filter-shift")?.value || order.shift_id || "";
        const returnUrl =
            currentShift && currentShift !== "ALL"
                ? `pos.html?shift_id=${encodeURIComponent(currentShift)}`
                : "pos.html";
        simLinkEl.href = `bank-simulator.html?order_code=${encodeURIComponent(order.order_code)}&amount=${encodeURIComponent(expectedAmount)}&return_url=${encodeURIComponent(returnUrl)}`;
    }

    const modalEl = document.getElementById("vietqrModal");
    if (modalEl) {
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
}"""

replacement_modal_js = """async function openOrderQrModal(orderId, shouldIssueIfMissing = true) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    currentSelectedOrderForQr = order;
    const isPaid = String(order.payment_status || "").toUpperCase() === "PAID";
    const totalAmount = Number(order.total_amount || 0);
    const paidAmount = Number(order.net_paid_amount ?? order.paid_amount ?? order.allocated_amount ?? 0);
    const remainingAmount = Math.max(0, totalAmount - paidAmount);

    const existingQr = order.qr_request || order.active_payment_request || order.active_qr;
    const qrAmountMismatch = existingQr && Math.round(Number(existingQr.expected_amount || 0)) !== Math.round(remainingAmount);

    // Nếu đơn hàng chưa thanh toán đủ và chưa có QR hoặc mã QR cũ không khớp với số tiền còn thiếu
    if (!isPaid && shouldIssueIfMissing && (!existingQr || existingQr.status !== "ACTIVE" || qrAmountMismatch)) {
        await issueDynamicVietQr(order.id, false);
    } else {
        displayQrInModal(order, existingQr);
    }
}

async function issueDynamicVietQr(orderId, isReissue = false) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    const paidAmount = Number(order.net_paid_amount ?? order.paid_amount ?? order.allocated_amount ?? 0);
    const remainingAmount = Math.max(0, Number(order.total_amount || 0) - paidAmount);
    const expected = remainingAmount > 0 ? remainingAmount : Number(order.total_amount || 0);

    try {
        const qrResp = await apiRequest("/payment-requests", {
            method: "POST",
            body: JSON.stringify({
                order_id: orderId,
                expected_amount: expected
            })
        });
        await loadPosOrders(false);
        const updatedOrder = posOrdersCache.find((o) => Number(o.id) === Number(orderId)) || order;
        displayQrInModal(updatedOrder, qrResp);
    } catch (error) {
        if (error.isNetworkError) {
            const store = getDemoStore();
            const target = store.orders.find((o) => Number(o.id) === Number(orderId));
            const simulatedQr = {
                request_code: `REQ-${order.order_code}-${Math.floor(10 + Math.random() * 89)}`,
                expected_amount: expected,
                status: "ACTIVE",
                qr_url: buildEmvcoVietQrUrl(order.order_code, expected),
                expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString()
            };
            if (target) {
                target.qr_request = simulatedQr;
                saveDemoStore(store);
                posOrdersCache = store.orders;
            }
            order.qr_request = simulatedQr;
            renderPosOrdersTable(posOrdersCache);
            displayQrInModal(order, simulatedQr);
        } else {
            showToast(error.message || "Không thể xuất mã QR.", "danger");
            return;
        }
    }

    showToast(
        isReissue ? `Đã đổi mã QR mới cho đơn ${order.order_code}` : `Đã tạo mã QR cho đơn ${order.order_code}`,
        "success"
    );
}

function displayQrInModal(order, qrData) {
    if (!order) return;
    currentSelectedOrderForQr = order;

    const isPaid = String(order.payment_status || "").toUpperCase() === "PAID";
    const totalAmount = Number(order.total_amount || 0);
    const paidAmount = Number(order.net_paid_amount ?? order.paid_amount ?? order.allocated_amount ?? 0);
    const remainingAmount = Math.max(0, totalAmount - paidAmount);
    const isPartial = String(order.payment_status || "").toUpperCase() === "PARTIALLY_PAID" || (!isPaid && paidAmount > 0 && remainingAmount > 0);

    // Xác định số tiền hiển thị trên QR: Với đơn chuyển thiếu, BẮT BUỘC là số tiền còn thiếu
    let expectedAmount;
    if (isPaid) {
        expectedAmount = paidAmount > 0 ? paidAmount : totalAmount;
    } else if (isPartial) {
        expectedAmount = remainingAmount;
    } else {
        expectedAmount = Math.round(Number(qrData?.expected_amount || remainingAmount || totalAmount));
    }

    // Nếu đơn hàng chưa thanh toán đủ hoặc chuyển thiếu, bảo đảm URL mã QR chứa đúng số tiền còn thiếu
    let qrUrl = qrData?.qr_url;
    if (!isPaid) {
        if (!qrUrl || isPartial || Math.round(Number(qrData?.expected_amount || 0)) !== expectedAmount) {
            qrUrl = buildEmvcoVietQrUrl(order.order_code, expectedAmount);
        }
    }

    const badgeEl = document.getElementById("modal-qr-status-badge");
    const titleEl = document.getElementById("modal-qr-title");
    const qrFrameBox = document.getElementById("modal-qr-frame-box");
    const actionsEl = document.getElementById("modal-qr-actions");
    const paidTimeRow = document.getElementById("modal-qr-paid-time-row");
    const paidTimeEl = document.getElementById("modal-qr-paid-time");

    if (badgeEl) {
        if (isPaid) {
            badgeEl.className = "fp-badge fp-badge-success mb-1";
            badgeEl.textContent = "✓ Đã thanh toán đủ";
        } else if (isPartial) {
            badgeEl.className = "fp-badge fp-badge-warning mb-1";
            badgeEl.textContent = "● Khách chuyển thiếu - Cần thu tiếp";
        } else {
            badgeEl.className = "fp-badge fp-badge-dark mb-1";
            badgeEl.textContent = "Mã QR đang hoạt động";
        }
    }

    if (titleEl) {
        if (isPaid) {
            titleEl.textContent = "Biên Lai Thanh Toán";
        } else if (isPartial) {
            titleEl.textContent = "Mã QR Thu Tiếp Số Tiền Còn Thiếu";
        } else {
            titleEl.textContent = "Quét Mã VietQR Thanh Toán";
        }
    }

    // Nếu đã thanh toán (Xem biên lai): Ẩn ảnh QR và ẩn 2 nút hành động, chỉ hiện các dòng thông tin biên lai
    if (qrFrameBox) {
        qrFrameBox.classList.toggle("d-none", isPaid);
    }
    if (actionsEl) {
        actionsEl.classList.toggle("d-none", isPaid);
    }
    if (paidTimeRow) {
        paidTimeRow.classList.toggle("d-none", !isPaid);
    }

    if (paidTimeEl && isPaid) {
        const txTime =
            order.paid_at ||
            order.last_payment_at ||
            qrData?.created_at ||
            order.created_at;
        paidTimeEl.textContent = formatDateTime(txTime);
    }

    const imgEl = document.getElementById("modal-qr-image");
    const ordCodeEl = document.getElementById("modal-qr-order-code");
    const amountEl = document.getElementById("modal-qr-expected-amount");
    const contentEl = document.getElementById("modal-qr-transfer-content");
    const simLinkEl = document.getElementById("modal-link-simulator");

    const totalRow = document.getElementById("modal-qr-total-row");
    const totalEl = document.getElementById("modal-qr-total-amount");
    const paidRow = document.getElementById("modal-qr-paid-amount-row");
    const paidEl = document.getElementById("modal-qr-paid-amount");
    const amountLabel = document.getElementById("modal-qr-amount-label");

    if (totalRow) totalRow.classList.toggle("d-none", !isPartial);
    if (paidRow) paidRow.classList.toggle("d-none", !isPartial);
    if (totalEl) totalEl.textContent = formatVND(totalAmount);
    if (paidEl) paidEl.textContent = formatVND(paidAmount);

    if (amountLabel) {
        if (isPaid) {
            amountLabel.textContent = "Số tiền đã thu:";
        } else if (isPartial) {
            amountLabel.textContent = "Số tiền còn thiếu:";
        } else {
            amountLabel.textContent = "Số tiền:";
        }
    }

    if (imgEl && !isPaid) imgEl.src = qrUrl;
    if (ordCodeEl) ordCodeEl.textContent = order.order_code;
    if (amountEl) {
        amountEl.textContent = formatVND(expectedAmount);
        if (isPartial) {
            amountEl.className = "text-danger fw-bold fs-5 font-numeric";
        } else {
            amountEl.className = "text-primary fw-bold fs-6 font-numeric";
        }
    }
    if (contentEl) {
        contentEl.textContent = order.last_transfer_content || `TT ${order.order_code}`;
    }

    if (simLinkEl) {
        const currentShift = document.getElementById("pos-filter-shift")?.value || order.shift_id || "";
        const returnUrl =
            currentShift && currentShift !== "ALL"
                ? `pos.html?shift_id=${encodeURIComponent(currentShift)}`
                : "pos.html";
        simLinkEl.href = `bank-simulator.html?order_code=${encodeURIComponent(order.order_code)}&amount=${encodeURIComponent(expectedAmount)}&return_url=${encodeURIComponent(returnUrl)}`;
        simLinkEl.textContent = isPartial ? "Thu tiếp đơn này →" : "Thanh toán đơn này →";
    }

    const modalEl = document.getElementById("vietqrModal");
    if (modalEl) {
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
}"""

assert target_modal_js in pos_js_norm, "Target modal JS not found"
pos_js_norm = pos_js_norm.replace(target_modal_js, replacement_modal_js)

if '\r\n' in pos_js:
    pos_js_norm = pos_js_norm.replace('\n', '\r\n')

with open('frontend/js/pos.js', 'w', encoding='utf-8') as f:
    f.write(pos_js_norm)

print("SUCCESS: frontend/js/pos.js updated")
