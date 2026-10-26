import sys

# 1. Update backend/routers/decisions.py
with open("backend/routers/decisions.py", "r", encoding="utf-8") as f:
    dec_code = f.read()

dec_norm = dec_code.replace("\r\n", "\n")

target_ovp_check_dec = """        is_ovp = bool(linked_order and float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0)"""
replacement_ovp_check_dec = """        is_ovp = False
        if linked_order:
            order_is_paid = (linked_order.payment_status == models.PaymentStatus.PAID)
            if float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0:
                is_ovp = True
            elif order_is_paid and float(tx.unallocated_amount or 0) > 0:
                is_ovp = True"""

assert target_ovp_check_dec in dec_norm, "target_ovp_check_dec not found"
dec_norm = dec_norm.replace(target_ovp_check_dec, replacement_ovp_check_dec)

# In make_decision: support converting APPROVE_MANUAL_MATCH to OVERPAYMENT_RESOLUTION when order is already PAID
target_paid_check = """        if order.payment_status == models.PaymentStatus.PAID:
            raise HTTPException(status_code=400, detail="Đơn hàng này đã được thanh toán đầy đủ.")"""

replacement_paid_check = """        if order.payment_status == models.PaymentStatus.PAID:
            # Nếu khách đã chuyển lại và đơn hàng đã thanh toán đủ: phần tiền này trở thành tiền thừa và được xử lý như đơn chuyển thừa
            decision_rec = models.Decision(
                order_id=order.id,
                bank_transaction_id=tx.id,
                reviewer_id=user.id,
                decision_type=models.DecisionType.OVERPAYMENT_RESOLUTION,
                reason=reason,
                challenge_used=challenge_used,
                assertion_signature=assertion_signature,
                biometric_verified=True
            )
            db.add(decision_rec)
            db.commit()
            db.refresh(decision_rec)
            return {
                "status": "success",
                "message": f"Hóa đơn {order.order_code} đã được thanh toán đủ (khách đã chuyển lại). Đã ghi nhận phương thức xử lý tiền thừa ({float(tx.unallocated_amount):,.0f} VNĐ) thành công.",
                "decision_id": decision_rec.id,
                "decision_type": "OVERPAYMENT_RESOLUTION",
                "bank_transaction_id": tx.id,
                "reference_code": tx.reference_code,
                "order_code": order.order_code,
                "unallocated_amount": float(tx.unallocated_amount),
                "handling_method": reason
            }"""

assert target_paid_check in dec_norm, "target_paid_check not found"
dec_norm = dec_norm.replace(target_paid_check, replacement_paid_check)

if "\r\n" in dec_code:
    dec_norm = dec_norm.replace("\n", "\r\n")

with open("backend/routers/decisions.py", "w", encoding="utf-8") as f:
    f.write(dec_norm)
print("SUCCESS: backend/routers/decisions.py updated")


# 2. Update backend/routers/dashboard.py
with open("backend/routers/dashboard.py", "r", encoding="utf-8") as f:
    dash_code = f.read()

dash_norm = dash_code.replace("\r\n", "\n")

target_ovp_dash = """        is_ovp = bool(linked_order and float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0)"""
replacement_ovp_dash = """        is_ovp = False
        if linked_order:
            order_is_paid = (linked_order.payment_status == models.PaymentStatus.PAID)
            if float(tx.allocated_amount or 0) > 0 and float(tx.unallocated_amount or 0) > 0:
                is_ovp = True
            elif order_is_paid and float(tx.unallocated_amount or 0) > 0:
                is_ovp = True"""

assert target_ovp_dash in dash_norm, "target_ovp_dash not found"
dash_norm = dash_norm.replace(target_ovp_dash, replacement_ovp_dash)

if "\r\n" in dash_code:
    dash_norm = dash_norm.replace("\n", "\r\n")

with open("backend/routers/dashboard.py", "w", encoding="utf-8") as f:
    f.write(dash_norm)
print("SUCCESS: backend/routers/dashboard.py updated")


# 3. Update frontend/reconciliation.html
with open("frontend/reconciliation.html", "r", encoding="utf-8") as f:
    html_code = f.read()

html_norm = html_code.replace("\r\n", "\n")

target_html_order_select = """                        <div class="mb-3">
                            <label for="match-order-select" class="form-label small fw-semibold">Chọn hóa đơn nhận tiền <span class="text-danger">*</span></label>
                            <select id="match-order-select" class="form-select" required></select>
                        </div>

                        <div class="mb-3">
                            <label for="match-amount-input" class="form-label small fw-semibold">Số tiền ghép vào hóa đơn (VNĐ) <span class="text-danger">*</span></label>
                            <input type="number" id="match-amount-input" class="form-control fw-bold font-numeric text-primary" required min="1000" step="1000">
                        </div>

                        <div class="mb-3">
                            <label for="match-reason-input" class="form-label small fw-semibold">Lý do xác nhận <span class="text-danger">*</span></label>
                            <textarea id="match-reason-input" class="form-control" rows="2" required>Khách hàng xác nhận chuyển khoản thanh toán cho hóa đơn nhưng quên ghi mã đơn.</textarea>
                        </div>"""

replacement_html_order_select = """                        <div class="mb-3">
                            <label for="match-order-select" class="form-label small fw-semibold">Chọn hóa đơn nhận tiền <span class="text-danger">*</span></label>
                            <select id="match-order-select" class="form-select" required></select>
                        </div>

                        <div id="match-paid-notice-box" class="alert alert-warning py-2 px-3 small mb-3 d-none"></div>

                        <div class="mb-3" id="match-amount-group">
                            <label for="match-amount-input" class="form-label small fw-semibold" id="match-amount-label">Số tiền ghép vào hóa đơn (VNĐ) <span class="text-danger">*</span></label>
                            <input type="number" id="match-amount-input" class="form-control fw-bold font-numeric text-primary" required min="1000" step="1000">
                        </div>

                        <div class="mb-3">
                            <label for="match-reason-input" class="form-label small fw-semibold" id="match-reason-label">Lý do xác nhận <span class="text-danger">*</span></label>
                            <textarea id="match-reason-input" class="form-control" rows="2" required placeholder="Nhập lý do hoặc phương thức xử lý..."></textarea>
                        </div>"""

assert target_html_order_select in html_norm, "target_html_order_select not found"
html_norm = html_norm.replace(target_html_order_select, replacement_html_order_select)

if "\r\n" in html_code:
    html_norm = html_norm.replace("\n", "\r\n")

with open("frontend/reconciliation.html", "w", encoding="utf-8") as f:
    f.write(html_norm)
print("SUCCESS: frontend/reconciliation.html updated")


# 4. Update frontend/js/reconciliation.js
with open("frontend/js/reconciliation.js", "r", encoding="utf-8") as f:
    js_code = f.read()

js_norm = js_code.replace("\r\n", "\n")

target_order_map = """        orderSelect.innerHTML = reconOrders
            .map((ord) => {
                const isCancelled = String(ord.order_status).toUpperCase() === "CANCELLED_ORDER";
                const rem = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));
                const statusLabel = isCancelled
                    ? "Đã hủy (Chặn ghép)"
                    : rem === 0
                    ? "Đã thu đủ"
                    : `Còn thiếu: ${formatVND(rem)}`;
                return `<option value="${ord.id}">Hóa đơn ${escapeReconHtml(ord.order_code)} — ${statusLabel}</option>`;
            })
            .join("");"""

replacement_order_map = """        orderSelect.innerHTML = reconOrders
            .map((ord) => {
                const isCancelled = String(ord.order_status).toUpperCase() === "CANCELLED_ORDER";
                const isPaid = String(ord.payment_status).toUpperCase() === "PAID";
                const rem = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));
                const statusLabel = isCancelled
                    ? "Đã hủy (Chặn ghép)"
                    : (isPaid || rem === 0)
                    ? "Đã thu đủ (Khách đã chuyển lại)"
                    : `Còn thiếu: ${formatVND(rem)}`;
                return `<option value="${ord.id}">Hóa đơn ${escapeReconHtml(ord.order_code)} — ${statusLabel}</option>`;
            })
            .join("");"""

assert target_order_map in js_norm, "target_order_map not found"
js_norm = js_norm.replace(target_order_map, replacement_order_map)

# Update updateSuggestedMatchAmount
target_update_suggested = """function updateSuggestedMatchAmount() {
    const txId = Number(document.getElementById("match-tx-id")?.value || 0);
    const orderId = Number(document.getElementById("match-order-select")?.value || 0);
    const amountInput = document.getElementById("match-amount-input");
    if (!amountInput) return;

    const tx = reconBankTxs.find((t) => Number(t.id) === txId);
    const ord = reconOrders.find((o) => Number(o.id) === orderId);
    if (!tx || !ord) return;

    const txUnalloc = Number(tx.unallocated_amount || 0);
    const ordRem = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));
    const suggested = ordRem > 0 ? Math.min(txUnalloc, ordRem) : txUnalloc;
    amountInput.value = String(suggested);
}"""

replacement_update_suggested = """function updateSuggestedMatchAmount() {
    const txId = Number(document.getElementById("match-tx-id")?.value || 0);
    const orderId = Number(document.getElementById("match-order-select")?.value || 0);
    const amountInput = document.getElementById("match-amount-input");
    const amountGroup = document.getElementById("match-amount-group");
    const amountLabel = document.getElementById("match-amount-label");
    const noticeBox = document.getElementById("match-paid-notice-box");
    const reasonLabel = document.getElementById("match-reason-label");
    const reasonInput = document.getElementById("match-reason-input");
    const confirmBtn = document.getElementById("btn-confirm-match");

    const tx = reconBankTxs.find((t) => Number(t.id) === txId);
    const ord = reconOrders.find((o) => Number(o.id) === orderId);
    if (!tx || !ord) return;

    const txUnalloc = Number(tx.unallocated_amount || 0);
    const isCancelled = String(ord.order_status).toUpperCase() === "CANCELLED_ORDER";
    const isPaid = String(ord.payment_status).toUpperCase() === "PAID";
    const ordRem = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));

    // Nếu đơn hàng đã thu đủ (khách đã chuyển lại): khoản tiền này trở thành tiền thừa và xử lý như đơn chuyển thừa
    if (!isCancelled && (isPaid || ordRem <= 0)) {
        if (amountInput) {
            amountInput.value = String(txUnalloc);
            amountInput.disabled = true;
        }
        if (amountLabel) {
            amountLabel.innerHTML = 'Số tiền chuyển thừa (VNĐ) <span class="badge bg-danger ms-1">Tiền thừa</span>';
        }
        if (noticeBox) {
            noticeBox.className = "alert alert-warning py-2 px-3 small mb-3";
            noticeBox.innerHTML = `
                <div class="fw-bold mb-1">💡 Hóa đơn ${escapeReconHtml(ord.order_code)} đã được thanh toán đủ (khách đã chuyển lại).</div>
                <div>Khoản tiền <strong>${formatVND(txUnalloc)}</strong> của giao dịch này trở thành <strong>TIỀN THỪA</strong> và được xử lý theo phương thức xử lý tiền thừa.</div>
            `;
            noticeBox.classList.remove("d-none");
        }
        if (reasonLabel) {
            reasonLabel.innerHTML = 'Phương thức xử lý tiền thừa <span class="text-danger">*</span>';
        }
        if (reasonInput) {
            if (!reasonInput.value || reasonInput.value.includes("Khách hàng xác nhận chuyển khoản thanh toán")) {
                reasonInput.value = `Khách hàng đã chuyển lại thanh toán đơn ${ord.order_code}, khoản chuyển sai nội dung này đã được xử lý hoàn trả tiền thừa cho khách.`;
            }
            reasonInput.placeholder = "Ghi rõ phương thức xử lý khoản tiền thừa (ví dụ: Đã hoàn tiền mặt cho khách tại quầy, chuyển khoản lại...)...";
        }
        if (confirmBtn) {
            confirmBtn.textContent = "Xác nhận xử lý tiền thừa";
            confirmBtn.className = "btn-fp-warning";
        }
    } else {
        // Đơn hàng còn phải thu
        if (amountInput) {
            amountInput.disabled = false;
            const suggested = ordRem > 0 ? Math.min(txUnalloc, ordRem) : txUnalloc;
            amountInput.value = String(suggested);
        }
        if (amountLabel) {
            amountLabel.innerHTML = 'Số tiền ghép vào hóa đơn (VNĐ) <span class="text-danger">*</span>';
        }
        if (noticeBox) {
            noticeBox.classList.add("d-none");
        }
        if (reasonLabel) {
            reasonLabel.innerHTML = 'Lý do xác nhận <span class="text-danger">*</span>';
        }
        if (reasonInput) {
            if (reasonInput.value.includes("khoản chuyển sai nội dung này đã được xử lý")) {
                reasonInput.value = "Khách hàng xác nhận chuyển khoản thanh toán cho hóa đơn nhưng quên ghi mã đơn.";
            }
            reasonInput.placeholder = "Nhập lý do xác nhận...";
        }
        if (confirmBtn) {
            confirmBtn.textContent = "Xác nhận";
            confirmBtn.className = "btn-fp-success";
        }
    }
}"""

assert target_update_suggested in js_norm, "target_update_suggested not found"
js_norm = js_norm.replace(target_update_suggested, replacement_update_suggested)

# Update handleManualMatchSubmit to submit OVERPAYMENT_RESOLUTION when ord is already paid
target_submit_match_start = """    const bankTxId = Number(document.getElementById("match-tx-id")?.value || 0);
    const orderId = Number(document.getElementById("match-order-select")?.value || 0);
    const manualAmount = Number(document.getElementById("match-amount-input")?.value || 0);
    const reason = (document.getElementById("match-reason-input")?.value || "").trim();
    const securityMode = document.getElementById("match-security-mode")?.value || "WEBAUTHN_SIGN";
    const errorBox = document.getElementById("match-error-box");

    if (errorBox) errorBox.classList.add("d-none");

    if (!reason || reason.length < 5) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập rõ lý do xác nhận (ít nhất 5 ký tự).";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    isSubmittingDecision = true;
    try {
        // Nếu chọn chế độ thử nghiệm bỏ qua khóa bảo mật (TC-06):
        // Gửi thẳng request không có chữ ký WebAuthn lên Backend để Server trả về đúng lỗi 401 Unauthorized
        if (securityMode === "BYPASS_WEBAUTHN_TEST") {
            await apiRequest("/decisions", {
                method: "POST",
                body: JSON.stringify({
                    reviewer_id: getCurrentUserId(),
                    decision_type: "APPROVE_MANUAL_MATCH",
                    bank_transaction_id: bankTxId,
                    order_id: orderId,
                    allocated_amount: manualAmount,
                    reason,
                    security_mode: "BYPASS_WEBAUTHN_TEST",
                    credential_id: null,
                    challenge_used: null,
                    assertion_signature: null
                })
            });
        } else {
            const webauthnProof = await requestWebAuthnAssertion({
                decision_type: "APPROVE_MANUAL_MATCH",
                order_id: orderId,
                bank_transaction_id: bankTxId
            });

            await apiRequest("/decisions", {
                method: "POST",
                body: JSON.stringify({
                    reviewer_id: getCurrentUserId(),
                    decision_type: "APPROVE_MANUAL_MATCH",
                    bank_transaction_id: bankTxId,
                    order_id: orderId,
                    allocated_amount: manualAmount,
                    reason,
                    security_mode: "WEBAUTHN_SIGN",
                    credential_id: webauthnProof.credential_id,
                    challenge_used: webauthnProof.challenge_used,
                    assertion_signature: webauthnProof.assertion_signature
                })
            });
        }"""

replacement_submit_match_start = """    const bankTxId = Number(document.getElementById("match-tx-id")?.value || 0);
    const orderId = Number(document.getElementById("match-order-select")?.value || 0);
    const manualAmount = Number(document.getElementById("match-amount-input")?.value || 0);
    const reason = (document.getElementById("match-reason-input")?.value || "").trim();
    const securityMode = document.getElementById("match-security-mode")?.value || "WEBAUTHN_SIGN";
    const errorBox = document.getElementById("match-error-box");

    if (errorBox) errorBox.classList.add("d-none");

    if (!reason || reason.length < 5) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập rõ lý do hoặc phương thức xử lý (ít nhất 5 ký tự).";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    const selectedOrd = reconOrders.find((o) => Number(o.id) === orderId);
    const isOrdPaid = selectedOrd && (
        String(selectedOrd.payment_status).toUpperCase() === "PAID" ||
        Math.max(0, Number(selectedOrd.total_amount || 0) - Number(selectedOrd.net_paid_amount || 0)) <= 0
    );

    // Nếu đơn hàng đã thu đủ (khách đã chuyển lại), tự động chuyển loại quyết định sang OVERPAYMENT_RESOLUTION
    const effectiveDecisionType = isOrdPaid ? "OVERPAYMENT_RESOLUTION" : "APPROVE_MANUAL_MATCH";

    isSubmittingDecision = true;
    try {
        if (securityMode === "BYPASS_WEBAUTHN_TEST") {
            await apiRequest("/decisions", {
                method: "POST",
                body: JSON.stringify({
                    reviewer_id: getCurrentUserId(),
                    decision_type: effectiveDecisionType,
                    bank_transaction_id: bankTxId,
                    order_id: orderId,
                    allocated_amount: isOrdPaid ? 0 : manualAmount,
                    reason,
                    security_mode: "BYPASS_WEBAUTHN_TEST",
                    credential_id: null,
                    challenge_used: null,
                    assertion_signature: null
                })
            });
        } else {
            const webauthnProof = await requestWebAuthnAssertion({
                decision_type: effectiveDecisionType,
                order_id: orderId,
                bank_transaction_id: bankTxId
            });

            await apiRequest("/decisions", {
                method: "POST",
                body: JSON.stringify({
                    reviewer_id: getCurrentUserId(),
                    decision_type: effectiveDecisionType,
                    bank_transaction_id: bankTxId,
                    order_id: orderId,
                    allocated_amount: isOrdPaid ? 0 : manualAmount,
                    reason,
                    security_mode: "WEBAUTHN_SIGN",
                    credential_id: webauthnProof.credential_id,
                    challenge_used: webauthnProof.challenge_used,
                    assertion_signature: webauthnProof.assertion_signature
                })
            });
        }"""

assert target_submit_match_start in js_norm, "target_submit_match_start not found"
js_norm = js_norm.replace(target_submit_match_start, replacement_submit_match_start)

if "\r\n" in js_code:
    js_norm = js_norm.replace("\n", "\r\n")

with open("frontend/js/reconciliation.js", "w", encoding="utf-8") as f:
    f.write(js_norm)
print("SUCCESS: frontend/js/reconciliation.js updated")
