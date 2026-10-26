import sys

with open("frontend/js/reconciliation.js", "r", encoding="utf-8") as f:
    js_content = f.read()

js_norm = js_content.replace("\r\n", "\n")

# 1. Update DECISION_TYPE_LABELS
target_labels = """const DECISION_TYPE_LABELS = {
    APPROVE_MANUAL_MATCH: "Ghép tiền vào hóa đơn",
    REVERSE_ALLOCATION: "Đảo bút toán đã ghép",
    REJECT_TX: "Từ chối giao dịch"
};"""

replacement_labels = """const DECISION_TYPE_LABELS = {
    APPROVE_MANUAL_MATCH: "Ghép tiền vào hóa đơn",
    REVERSE_ALLOCATION: "Đảo bút toán đã ghép",
    REJECT_TX: "Từ chối giao dịch",
    OVERPAYMENT_RESOLUTION: "Ghi nhận xử lý tiền thừa"
};"""

assert target_labels in js_norm, "target_labels not found"
js_norm = js_norm.replace(target_labels, replacement_labels)

# 2. Update bindReconciliationEvents
target_bind = """    document.getElementById("match-order-select")?.addEventListener("change", updateSuggestedMatchAmount);
    document.getElementById("form-manual-match")?.addEventListener("submit", handleManualMatchSubmit);
    document.getElementById("form-reverse-alloc")?.addEventListener("submit", handleReverseAllocSubmit);"""

replacement_bind = """    document.getElementById("match-order-select")?.addEventListener("change", updateSuggestedMatchAmount);
    document.getElementById("form-manual-match")?.addEventListener("submit", handleManualMatchSubmit);
    document.getElementById("form-overpayment")?.addEventListener("submit", handleOverpaymentSubmit);
    document.getElementById("form-reverse-alloc")?.addEventListener("submit", handleReverseAllocSubmit);"""

assert target_bind in js_norm, "target_bind not found"
js_norm = js_norm.replace(target_bind, replacement_bind)

# 3. Update renderUnmatchedTable
target_render_unmatched = """    tbody.innerHTML = exceptionTxs
        .map((tx) => {
            const unalloc = Number(tx.unallocated_amount || 0);
            return `
                <tr>
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(tx.reference_code)}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(tx.created_at)}</div>
                    </td>
                    <td>
                        <span class="fw-medium text-dark">${escapeReconHtml(tx.transfer_content)}</span>
                    </td>
                    <td class="text-end font-numeric">
                        ${formatVND(tx.amount)}
                    </td>
                    <td class="text-end fw-bold text-danger font-numeric">
                        ${formatVND(unalloc)}
                    </td>
                    <td>
                        ${renderStatusBadge(tx.match_status || "UNMATCHED")}
                    </td>
                    <td class="text-end">
                        <button type="button" class="btn-fp-dark py-1 px-3" style="font-size: 0.8rem;" onclick="openManualMatchModal(${tx.id})">
                            Ghép vào hóa đơn
                        </button>
                    </td>
                </tr>
            `;
        })
        .join("");"""

replacement_render_unmatched = """    tbody.innerHTML = exceptionTxs
        .map((tx) => {
            const unalloc = Number(tx.unallocated_amount || 0);
            const isHandled = Boolean(
                tx.is_handled ||
                (reconDecisions && reconDecisions.some((d) => Number(d.bank_transaction_id) === Number(tx.id)))
            );

            return `
                <tr id="row-recon-tx-${tx.id}">
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(tx.reference_code)}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(tx.created_at)}</div>
                    </td>
                    <td>
                        <span class="fw-medium text-dark">${escapeReconHtml(tx.transfer_content)}</span>
                    </td>
                    <td class="text-end font-numeric">
                        ${formatVND(tx.amount)}
                    </td>
                    <td class="text-end fw-bold text-danger font-numeric">
                        ${formatVND(unalloc)}
                    </td>
                    <td>
                        ${renderStatusBadge(tx.match_status || "UNMATCHED")}
                    </td>
                    <td class="text-end" id="action-cell-tx-${tx.id}">
                        ${
                            isHandled
                                ? `<button type="button" class="btn btn-sm btn-success py-1 px-3" disabled style="font-size: 0.8rem; background-color: #198754; border-color: #198754; color: #fff; cursor: default; opacity: 1;">
                                       ✓ Đã xử lý
                                   </button>`
                                : `<button type="button" class="btn-fp-dark py-1 px-3" id="btn-handle-tx-${tx.id}" style="font-size: 0.8rem;" onclick="handleTransactionAction(${tx.id})">
                                       Xử lý
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");"""

assert target_render_unmatched in js_norm, "target_render_unmatched not found"
js_norm = js_norm.replace(target_render_unmatched, replacement_render_unmatched)

# 4. Update renderDecisionsHistory
target_render_history = """// 3. Lịch sử phê duyệt
function renderDecisionsHistory() {
    const listEl = document.getElementById("recon-decisions-list");
    if (!listEl) return;

    if (!reconDecisions || reconDecisions.length === 0) {
        listEl.innerHTML = `<div class="text-center py-4 text-secondary small">Chưa có lịch sử phê duyệt nào.</div>`;
        return;
    }

    listEl.innerHTML = reconDecisions
        .map((d) => {
            const label = DECISION_TYPE_LABELS[d.decision_type] || d.decision_type;
            return `
                <div class="p-3 rounded-3 bg-light border small d-flex flex-wrap align-items-center justify-content-between gap-2">
                    <div>
                        <div class="fw-bold text-dark mb-1">
                            ${escapeReconHtml(label)} • Giao dịch ${escapeReconHtml(d.reference_code || `#${d.bank_transaction_id}`)} → Hóa đơn ${escapeReconHtml(d.order_code || `#${d.order_id}`)}
                        </div>
                        <div class="text-secondary">Lý do: “${escapeReconHtml(d.reason)}”</div>
                    </div>
                    <div class="text-end">
                        <span class="fp-badge fp-badge-success mb-1">✓ Đã xác thực bảo mật</span>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(d.review_date || d.created_at)}</div>
                    </div>
                </div>
            `;
        })
        .join("");
}"""

replacement_render_history = """// 3. Lịch sử phê duyệt
function renderDecisionsHistory() {
    const listEl = document.getElementById("recon-decisions-list");
    if (!listEl) return;

    if (!reconDecisions || reconDecisions.length === 0) {
        listEl.innerHTML = `<div class="text-center py-4 text-secondary small">Chưa có lịch sử phê duyệt nào.</div>`;
        return;
    }

    listEl.innerHTML = reconDecisions
        .map((d) => {
            const typeLabel = DECISION_TYPE_LABELS[d.decision_type] || d.decision_type;
            const isOvp = d.decision_type === "OVERPAYMENT_RESOLUTION";
            const badgeClass = isOvp ? "fp-badge-warning" : d.decision_type === "REVERSE_ALLOCATION" ? "fp-badge-danger" : "fp-badge-dark";
            
            const txCode = d.reference_code || (d.bank_transaction_id ? `GD #${d.bank_transaction_id}` : "—");
            const ordCode = d.order_code ? `Hóa đơn ${d.order_code}` : (d.order_id ? `Hóa đơn #${d.order_id}` : "Không có");
            const reviewerName = d.reviewer_name || `Nhân viên #${d.reviewer_id || 1}`;

            let amountInfo = "";
            if (d.tx_amount != null) {
                amountInfo += `<span class="me-2">Số tiền GD: <strong>${formatVND(d.tx_amount)}</strong></span>`;
            }
            if (d.allocated_amount != null && d.allocated_amount > 0) {
                amountInfo += `<span class="text-success me-2">Đã phân bổ: <strong>${formatVND(d.allocated_amount)}</strong></span>`;
            }
            if (d.unallocated_amount != null && d.unallocated_amount > 0) {
                amountInfo += `<span class="text-danger me-2">Tiền thừa: <strong>${formatVND(d.unallocated_amount)}</strong></span>`;
            }

            const verifiedBadge = d.biometric_verified
                ? `<span class="fp-badge fp-badge-success mb-1">✓ Đã xác thực bảo mật WebAuthn</span>`
                : `<span class="fp-badge fp-badge-neutral mb-1">Chưa qua khóa bảo mật</span>`;

            return `
                <div class="p-3 rounded-3 bg-light border small d-flex flex-wrap align-items-center justify-content-between gap-3">
                    <div style="max-width: 70%;">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="fp-badge ${badgeClass}">${escapeReconHtml(typeLabel)}</span>
                            <strong class="text-dark font-numeric">${escapeReconHtml(txCode)}</strong>
                            <span class="text-secondary">→</span>
                            <strong class="text-primary">${escapeReconHtml(ordCode)}</strong>
                        </div>
                        ${amountInfo ? `<div class="mb-1 text-secondary" style="font-size: 0.78rem;">${amountInfo}</div>` : ""}
                        <div class="text-dark fw-medium">
                            ${isOvp ? "Phương thức xử lý:" : "Lý do:"}
                            <span class="fw-normal text-secondary">“${escapeReconHtml(d.reason)}”</span>
                        </div>
                        <div class="text-secondary mt-1" style="font-size: 0.72rem;">
                            Thực hiện bởi: <strong>${escapeReconHtml(reviewerName)}</strong>
                        </div>
                    </div>
                    <div class="text-end">
                        ${verifiedBadge}
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(d.review_date || d.created_at)}</div>
                    </div>
                </div>
            `;
        })
        .join("");
}"""

assert target_render_history in js_norm, "target_render_history not found"
js_norm = js_norm.replace(target_render_history, replacement_render_history)

# 5. Add handleTransactionAction & openOverpaymentModal & handleOverpaymentSubmit before openManualMatchModal
target_open_match = """// 4. Mở hộp thoại Ghép tiền vào hóa đơn
function openManualMatchModal(txId) {"""

replacement_actions = """// 4. Xác định loại giao dịch và điều hướng mở hộp thoại tương ứng
function handleTransactionAction(txId) {
    const tx = reconBankTxs.find((t) => Number(t.id) === Number(txId));
    if (!tx) return;

    // Giao dịch chuyển thừa tiền: Đã có phân bổ > 0 và số tiền còn thừa > 0, hoặc có gắn với hóa đơn
    const isOverpayment = Boolean(
        tx.is_overpayment ||
        (Number(tx.allocated_amount || 0) > 0 && Number(tx.unallocated_amount || 0) > 0)
    );

    if (isOverpayment) {
        openOverpaymentModal(txId);
    } else {
        openManualMatchModal(txId);
    }
}

// 4.1 Mở hộp thoại Phương thức xử lý (giao dịch chuyển thừa)
function openOverpaymentModal(txId) {
    const tx = reconBankTxs.find((t) => Number(t.id) === Number(txId));
    if (!tx) return;

    document.getElementById("ovp-tx-id").value = String(tx.id);
    document.getElementById("ovp-order-id").value = String(tx.order_id || "");

    document.getElementById("ovp-tx-code").textContent = tx.reference_code || "—";
    document.getElementById("ovp-order-code").textContent = tx.order_code ? `Hóa đơn ${tx.order_code}` : (tx.order_id ? `Hóa đơn #${tx.order_id}` : "Hóa đơn liên quan");
    document.getElementById("ovp-tx-amount").textContent = formatVND(tx.amount);
    document.getElementById("ovp-order-amount").textContent = formatVND(tx.order_amount || tx.allocated_amount || 0);
    document.getElementById("ovp-unallocated-amount").textContent = formatVND(tx.unallocated_amount);

    const methodInput = document.getElementById("ovp-method-input");
    if (methodInput) methodInput.value = "";
    document.getElementById("ovp-error-box")?.classList.add("d-none");

    const modalEl = document.getElementById("overpaymentModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

// 4.2 Xử lý xác nhận Phương thức xử lý khoản tiền thừa
async function handleOverpaymentSubmit(event) {
    event.preventDefault();
    if (isSubmittingDecision) return;

    const txId = Number(document.getElementById("ovp-tx-id")?.value || 0);
    const orderId = Number(document.getElementById("ovp-order-id")?.value || 0) || null;
    const methodPlan = (document.getElementById("ovp-method-input")?.value || "").trim();
    const securityMode = document.getElementById("ovp-security-mode")?.value || "WEBAUTHN_SIGN";
    const errorBox = document.getElementById("ovp-error-box");
    const confirmBtn = document.getElementById("btn-confirm-ovp");

    if (errorBox) errorBox.classList.add("d-none");

    if (!methodPlan) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập phương thức xử lý khoản tiền thừa (không được để trống).";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    isSubmittingDecision = true;
    const oldBtnText = confirmBtn ? confirmBtn.innerHTML : "";
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Đang lưu...`;
    }

    try {
        let webauthnProof = {
            credential_id: null,
            challenge_used: null,
            assertion_signature: null
        };

        if (securityMode === "WEBAUTHN_SIGN") {
            try {
                webauthnProof = await requestWebAuthnAssertion({
                    decision_type: "OVERPAYMENT_RESOLUTION",
                    bank_transaction_id: txId,
                    order_id: orderId
                });
            } catch (err) {
                // Nếu người dùng hủy hoặc lỗi sinh trắc học
                if (errorBox) {
                    errorBox.textContent = err.message || "Xác thực bảo mật WebAuthn thất bại.";
                    errorBox.classList.remove("d-none");
                }
                isSubmittingDecision = false;
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = oldBtnText;
                }
                return;
            }
        }

        const resp = await apiRequest("/decisions", {
            method: "POST",
            body: JSON.stringify({
                reviewer_id: getCurrentUserId(),
                decision_type: "OVERPAYMENT_RESOLUTION",
                bank_transaction_id: txId,
                order_id: orderId,
                reason: methodPlan,
                security_mode: securityMode,
                credential_id: webauthnProof.credential_id,
                challenge_used: webauthnProof.challenge_used,
                assertion_signature: webauthnProof.assertion_signature
            })
        });

        // 1. Đóng hộp thoại
        const modalEl = document.getElementById("overpaymentModal");
        if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();

        // 2. Cập nhật nút thành "Đã xử lý" (màu xanh, vô hiệu hóa) trên giao diện ngay lập tức
        const actionCell = document.getElementById(`action-cell-tx-${txId}`);
        if (actionCell) {
            actionCell.innerHTML = `
                <button type="button" class="btn btn-sm btn-success py-1 px-3" disabled style="font-size: 0.8rem; background-color: #198754; border-color: #198754; color: #fff; cursor: default; opacity: 1;">
                    ✓ Đã xử lý
                </button>
            `;
        }

        // 3. Đánh dấu tx trong bộ nhớ là đã xử lý
        const targetTx = reconBankTxs.find((t) => Number(t.id) === txId);
        if (targetTx) {
            targetTx.is_handled = true;
            targetTx.handling_method = methodPlan;
        }

        // 4. Ghi nhận vào lịch sử phê duyệt
        reconDecisions.unshift({
            id: resp.decision_id || Date.now(),
            order_id: orderId,
            order_code: resp.order_code || (targetTx ? targetTx.order_code : null),
            bank_transaction_id: txId,
            reference_code: resp.reference_code || (targetTx ? targetTx.reference_code : null),
            tx_amount: targetTx ? targetTx.amount : null,
            allocated_amount: targetTx ? targetTx.allocated_amount : null,
            unallocated_amount: targetTx ? targetTx.unallocated_amount : null,
            reviewer_id: getCurrentUserId(),
            reviewer_name: "Quản trị viên",
            decision_type: "OVERPAYMENT_RESOLUTION",
            reason: methodPlan,
            biometric_verified: securityMode === "WEBAUTHN_SIGN",
            review_date: new Date().toISOString()
        });
        renderDecisionsHistory();

        showToast("Đã ghi nhận phương thức xử lý tiền thừa thành công!", "success");
    } catch (error) {
        if (errorBox) {
            errorBox.textContent = error.message || "Xử lý thất bại.";
            errorBox.classList.remove("d-none");
        }
        showToast(error.message || "Xử lý thất bại.", "danger");
    } finally {
        isSubmittingDecision = false;
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = oldBtnText;
        }
    }
}

// 4.3 Mở hộp thoại Ghép tiền vào hóa đơn
function openManualMatchModal(txId) {"""

assert target_open_match in js_norm, "target_open_match not found"
js_norm = js_norm.replace(target_open_match, replacement_actions)

# 6. Update handleManualMatchSubmit on success to update button immediately
target_manual_match_finish = """    isSubmittingDecision = false;
    const modalEl = document.getElementById("manualMatchModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
    showToast("Đã ghép khoản tiền vào hóa đơn thành công!", "success");
    loadReconciliationWorkspace(false);"""

replacement_manual_match_finish = """    isSubmittingDecision = false;
    const modalEl = document.getElementById("manualMatchModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();

    // Cập nhật nút thành Đã xử lý ngay lập tức trên giao diện
    const actionCell = document.getElementById(`action-cell-tx-${bankTxId}`);
    if (actionCell) {
        actionCell.innerHTML = `
            <button type="button" class="btn btn-sm btn-success py-1 px-3" disabled style="font-size: 0.8rem; background-color: #198754; border-color: #198754; color: #fff; cursor: default; opacity: 1;">
                ✓ Đã xử lý
            </button>
        `;
    }

    const targetTx = reconBankTxs.find((t) => Number(t.id) === bankTxId);
    if (targetTx) {
        targetTx.is_handled = true;
    }

    showToast("Đã ghép khoản tiền vào hóa đơn thành công!", "success");
    loadReconciliationWorkspace(false);"""

assert target_manual_match_finish in js_norm, "target_manual_match_finish not found"
js_norm = js_norm.replace(target_manual_match_finish, replacement_manual_match_finish)

if "\r\n" in js_content:
    js_norm = js_norm.replace("\n", "\r\n")

with open("frontend/js/reconciliation.js", "w", encoding="utf-8") as f:
    f.write(js_norm)

print("SUCCESS: frontend/js/reconciliation.js updated")
