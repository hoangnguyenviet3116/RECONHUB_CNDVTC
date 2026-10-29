// ==========================================================================
// ĐỐI SOÁT GIAO DỊCH LỆCH & HOÀN ĐẢO BÚT TOÁN (frontend/js/reconciliation.js)
// ==========================================================================

let reconBankTxs = [];
let reconOrders = [];
let reconAllocations = [];
let reconDecisions = [];
let isSubmittingDecision = false;

const DECISION_TYPE_LABELS = {
    APPROVE_MANUAL_MATCH: "Ghép tiền vào hóa đơn",
    REVERSE_ALLOCATION: "Đảo bút toán đã ghép",
    REJECT_TX: "Từ chối giao dịch",
    OVERPAYMENT_RESOLUTION: "Ghi nhận xử lý tiền thừa"
};

function initReconciliationPage() {
    if (typeof updateWebAuthnStatusBadge === "function") {
        updateWebAuthnStatusBadge();
    }
    bindReconciliationEvents();
    loadReconciliationWorkspace(false);
}

function bindReconciliationEvents() {
    document.getElementById("btn-webauthn-register")?.addEventListener("click", handleRegisterWebAuthnClick);
    document.getElementById("btn-recon-refresh")?.addEventListener("click", () => loadReconciliationWorkspace(true));

    document.getElementById("match-order-select")?.addEventListener("change", updateSuggestedMatchAmount);
    document.getElementById("form-manual-match")?.addEventListener("submit", handleManualMatchSubmit);
    document.getElementById("form-overpayment")?.addEventListener("submit", handleOverpaymentSubmit);
    document.getElementById("form-reverse-alloc")?.addEventListener("submit", handleReverseAllocSubmit);
}

async function handleRegisterWebAuthnClick() {
    const btn = document.getElementById("btn-webauthn-register");
    const oldHtml = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Đang kích hoạt...`;
    }
    try {
        await registerWebAuthnCredential();
        showToast("Đã kích hoạt khóa bảo mật trên thiết bị!", "success");
    } catch (error) {
        showToast(error.message || "Không thể đăng ký khóa bảo mật.", "danger");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = oldHtml;
        }
    }
}

async function loadReconciliationWorkspace(showNotification = false) {
    try {
        const [summaryRes, ordersRes] = await Promise.all([
            apiRequest("/dashboard/summary"),
            apiRequest("/orders").catch(() => [])
        ]);

        const orders = Array.isArray(ordersRes) ? ordersRes : (ordersRes.items || ordersRes.orders || []);
        reconOrders = Array.isArray(orders) ? orders : [];
        reconBankTxs = Array.isArray(summaryRes.bank_transactions) ? summaryRes.bank_transactions : (Array.isArray(summaryRes.recent_bank_transactions) ? summaryRes.recent_bank_transactions : []);
        reconAllocations = Array.isArray(summaryRes.payment_allocations) ? summaryRes.payment_allocations : (Array.isArray(summaryRes.ledger_entries) ? summaryRes.ledger_entries : []);
        reconDecisions = Array.isArray(summaryRes.decisions) ? summaryRes.decisions : (Array.isArray(summaryRes.recent_decisions) ? summaryRes.recent_decisions : []);
    } catch (_) {
        const store = getDemoStore();
        reconOrders = store.orders || [];
        reconBankTxs = store.bank_transactions || [];
        reconAllocations = store.allocations || [];
        reconDecisions = store.decisions || [];
    }

    renderUnmatchedTable();
    renderAllocationsTable();
    renderDecisionsHistory();

    if (showNotification) {
        showToast("Đã làm mới dữ liệu đối soát.", "success");
    }
}

// 1. Bảng các khoản tiền chờ xử lý (Phong cách mới đồng bộ thiết kế)
function renderUnmatchedTable() {
    const tbody = document.getElementById("recon-unmatched-tbody");
    const countBadge = document.getElementById("badge-unmatched-count");
    const todoPill = document.getElementById("unmatched-todo-pill");
    if (!tbody) return;

    // Các khoản đã được xử lý sẽ không hiện ở tab chờ xử lý nữa
    const pendingTxs = (reconBankTxs || []).filter((tx) => {
        const isHandled = Boolean(
            tx.is_handled ||
            (reconDecisions && reconDecisions.some((d) => Number(d.bank_transaction_id) === Number(tx.id)))
        );
        if (isHandled) return false;
        return Number(tx.unallocated_amount || 0) > 0 || String(tx.match_status || "").toUpperCase() === "UNMATCHED";
    });

    const count = pendingTxs.length;
    if (countBadge) {
        countBadge.textContent = String(count);
        countBadge.classList.toggle("d-none", count === 0);
    }
    if (todoPill) {
        todoPill.textContent = `${count} việc cần làm`;
        todoPill.classList.toggle("d-none", count === 0);
    }

    if (pendingTxs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-5 text-secondary">
                    <div class="fw-semibold text-success mb-1">✓ Đã đối soát tất cả các khoản chuyển khoản</div>
                    <span class="small">Không có giao dịch nào đang chờ phân bổ.</span>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = pendingTxs
        .map((tx) => {
            const unalloc = Number(tx.unallocated_amount || 0);

            // Xác định loại vấn đề (Issue pill)
            const isOverpayment = Boolean(
                tx.is_overpayment ||
                (Number(tx.allocated_amount || 0) > 0 && Number(tx.unallocated_amount || 0) > 0)
            );
            const content = (tx.transfer_content || "").toLowerCase();
            const reason = (tx.unmatched_reason || "").toLowerCase();

            let issueBadgeHtml = "";
            if (isOverpayment) {
                issueBadgeHtml = `<span class="badge-recon-warning">Chuyển dư tiền</span>`;
            } else if (reason.includes("nội dung") || reason.includes("sai") || content.includes("ban") || content.includes("bàn") || content.includes("hd") || content.includes("don")) {
                issueBadgeHtml = `<span class="badge-recon-warning">Sai nội dung</span>`;
            } else {
                issueBadgeHtml = `<span class="badge-recon-danger">Chưa rõ đơn</span>`;
            }

            return `
                <tr id="row-recon-tx-${tx.id}">
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(tx.reference_code)}</div>
                        <div class="text-secondary" style="font-size: 0.75rem;">${formatDateTime(tx.created_at)}</div>
                    </td>
                    <td>
                        <span class="fw-semibold text-dark">${escapeReconHtml(tx.transfer_content)}</span>
                    </td>
                    <td>
                        ${issueBadgeHtml}
                    </td>
                    <td>
                        <span class="fw-bold font-numeric text-dark" style="font-size: 0.95rem;">${formatVND(unalloc)}</span>
                    </td>
                    <td class="text-end" id="action-cell-tx-${tx.id}">
                        <button type="button" class="btn-recon-white" id="btn-handle-tx-${tx.id}" onclick="handleTransactionAction(${tx.id})">
                            Xử lý ngay
                        </button>
                    </td>
                </tr>
            `;
        })
        .join("");
}

// 2. Bảng các khoản đã khớp & hoàn đảo
function renderAllocationsTable() {
    const tbody = document.getElementById("recon-allocations-tbody");
    if (!tbody) return;

    if (!reconAllocations || reconAllocations.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-5 text-secondary">
                    Chưa có bút toán phân bổ nào.
                </td>
            </tr>
        `;
        return;
    }

    const reversedOriginIds = new Set(
        reconAllocations
            .filter((a) => String(a.entry_type).toUpperCase() === "REVERSAL" && a.reversal_of_id)
            .map((a) => Number(a.reversal_of_id))
    );

    tbody.innerHTML = reconAllocations
        .map((alloc) => {
            const isReversal = String(alloc.entry_type || "").toUpperCase() === "REVERSAL" || Number(alloc.allocated_amount) < 0;
            const alreadyReversed = reversedOriginIds.has(Number(alloc.id));
            const amount = Number(alloc.allocated_amount || 0);

            // Tìm hóa đơn liên kết để lấy mô tả bàn / món ăn nếu có
            const matchedOrd = (reconOrders || []).find((o) => Number(o.id) === Number(alloc.order_id));
            const orderDesc = matchedOrd && matchedOrd.items_summary
                ? matchedOrd.items_summary
                : matchedOrd && matchedOrd.table_number
                ? `Bàn ${matchedOrd.table_number}`
                : "Thanh toán đơn hàng";

            const orderDisplayCode = alloc.order_code
                ? (alloc.order_code.startsWith("HD") ? alloc.order_code : `HD-${alloc.order_code.replace(/^(ORD|HD)-?/i, '')}`)
                : `HD #${alloc.order_id}`;

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(alloc.reference_code || `GD #${alloc.bank_transaction_id}`)}</div>
                        <div class="text-secondary" style="font-size: 0.75rem;">${formatDateTime(alloc.created_at)}</div>
                    </td>
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(orderDisplayCode)}</div>
                        <div class="text-secondary" style="font-size: 0.75rem;">${escapeReconHtml(orderDesc)}</div>
                    </td>
                    <td>
                        <span class="fw-bold font-numeric text-dark" style="font-size: 0.95rem;">${formatVND(amount)}</span>
                    </td>
                    <td>
                        <div class="d-flex align-items-center gap-1.5 text-secondary" style="font-size: 0.85rem;">
                            <svg class="hi-icon hi-icon-sm text-muted" viewBox="0 0 24 24">
                                <path d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"/>
                            </svg>
                            <span>${escapeReconHtml(alloc.reviewer_name || "Thu ngân")}</span>
                        </div>
                    </td>
                    <td class="text-end">
                        ${
                            isReversal
                                ? `<span class="small text-secondary">Bút toán đảo</span>`
                                : alreadyReversed
                                ? `<span class="badge bg-light text-secondary border">Đã hoàn đảo</span>`
                                : `<button type="button" class="btn btn-sm btn-link text-danger text-decoration-none fw-semibold p-0" onclick="openReverseModal(${alloc.id})">
                                       Đảo giao dịch
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}

// 3. Lịch sử phê duyệt (Hiển thị dạng bảng trực quan đồng bộ thiết kế)
function renderDecisionsHistory() {
    const tbody = document.getElementById("recon-decisions-tbody");
    const listEl = document.getElementById("recon-decisions-list");
    if (!tbody && !listEl) return;

    if (!reconDecisions || reconDecisions.length === 0) {
        const emptyHtml = `
            <tr>
                <td colspan="5" class="text-center py-5 text-secondary">
                    Chưa có lịch sử phê duyệt nào.
                </td>
            </tr>
        `;
        if (tbody) tbody.innerHTML = emptyHtml;
        if (listEl) listEl.innerHTML = `<div class="text-center py-4 text-secondary small">Chưa có lịch sử phê duyệt nào.</div>`;
        return;
    }

    const rowsHtml = reconDecisions
        .map((d) => {
            const txCode = d.reference_code || (d.bank_transaction_id ? `GD #${d.bank_transaction_id}` : "—");
            const ordCode = d.order_code
                ? (d.order_code.startsWith("HD") ? d.order_code : `HD-${d.order_code.replace(/^(ORD|HD)-?/i, '')}`)
                : (d.order_id ? `HD #${d.order_id}` : "Không có");
            const reviewerName = d.reviewer_name || `Quản trị viên`;

            let actionText = "";
            if (d.decision_type === "APPROVE_MANUAL_MATCH") {
                actionText = `Ghép giao dịch ${txCode} vào ${ordCode}`;
            } else if (d.decision_type === "REVERSE_ALLOCATION") {
                actionText = `Đảo giao dịch ${txCode}`;
            } else if (d.decision_type === "OVERPAYMENT_RESOLUTION") {
                actionText = `Xử lý tiền thừa cho ${ordCode}`;
            } else {
                actionText = DECISION_TYPE_LABELS[d.decision_type] || d.decision_type;
            }

            // Tách thời gian và ngày
            const dRaw = d.review_date || d.created_at;
            let timeStr = "—";
            let dateStr = "";
            if (dRaw) {
                const dt = new Date(String(dRaw).replace(" ", "T"));
                if (!isNaN(dt.getTime())) {
                    timeStr = dt.toLocaleTimeString("vi-VN", { hour12: false });
                    dateStr = dt.toLocaleDateString("vi-VN", { year: "numeric", month: "2-digit", day: "2-digit" });
                }
            }

            const isAuto = d.security_mode === "SYSTEM_AUTO" || d.allocation_mode === "AUTO";
            const methodPill = isAuto
                ? `<span class="badge-recon-green">Tự động</span>`
                : `<span class="badge-recon-blue">Thủ công</span>`;

            const fidoBadge = d.biometric_verified
                ? `<span class="badge bg-success-subtle text-success border border-success-subtle ms-1" style="font-size: 0.72rem;" title="Xác thực khóa bảo mật FIDO2 ECDSA P-256">✓ FIDO2</span>`
                : "";

            return `
                <tr>
                    <td>
                        <div class="fw-semibold text-dark font-numeric">${timeStr}</div>
                        <div class="text-secondary" style="font-size: 0.75rem;">${dateStr}</div>
                    </td>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <div class="rounded-circle bg-light d-flex align-items-center justify-content-center text-secondary border" style="width: 26px; height: 26px; font-size: 0.75rem;">
                                <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24">
                                    <path d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"/>
                                </svg>
                            </div>
                            <span class="fw-medium text-dark">${escapeReconHtml(reviewerName)}</span>
                        </div>
                    </td>
                    <td>
                        <div class="fw-semibold text-dark">${escapeReconHtml(actionText)}</div>
                        <div class="text-secondary small mt-0.5">“${escapeReconHtml(d.reason || "Đối soát giao dịch")}”</div>
                    </td>
                    <td>
                        <div class="fw-semibold text-primary font-numeric">${escapeReconHtml(ordCode)}</div>
                        <div class="text-secondary font-numeric" style="font-size: 0.75rem;">${escapeReconHtml(txCode)}</div>
                    </td>
                    <td>
                        ${methodPill}${fidoBadge}
                    </td>
                </tr>
            `;
        })
        .join("");

    if (tbody) tbody.innerHTML = rowsHtml;
}

// 4. Xác định loại giao dịch và điều hướng mở hộp thoại tương ứng
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
                assertion_signature: webauthnProof.assertion_signature,
                client_data_json: webauthnProof.client_data_json,
                authenticator_data: webauthnProof.authenticator_data
            })
        });

        // 1. Đóng hộp thoại
        const modalEl = document.getElementById("overpaymentModal");
        if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();

        // 2. Đánh dấu tx trong bộ nhớ là đã xử lý
        const targetTx = reconBankTxs.find((t) => Number(t.id) === txId);
        if (targetTx) {
            targetTx.is_handled = true;
            targetTx.handling_method = methodPlan;
        }

        // 3. Ghi nhận vào lịch sử phê duyệt
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

        // 4. Các khoản đã xử lý sẽ không hiện ở tab chờ xử lý nữa
        renderUnmatchedTable();
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
function openManualMatchModal(txId) {
    const tx = reconBankTxs.find((t) => Number(t.id) === Number(txId));
    if (!tx) return;

    document.getElementById("match-tx-id").value = String(tx.id);
    document.getElementById("match-tx-code").textContent = tx.reference_code;
    document.getElementById("match-tx-content").textContent = tx.transfer_content;
    document.getElementById("match-tx-unallocated").textContent = formatVND(tx.unallocated_amount);
    document.getElementById("match-error-box")?.classList.add("d-none");

    const orderSelect = document.getElementById("match-order-select");
    if (orderSelect) {
        orderSelect.innerHTML = reconOrders
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
            .join("");

        const firstUnpaidValid = reconOrders.find(
            (o) =>
                String(o.order_status).toUpperCase() !== "CANCELLED_ORDER" &&
                Math.max(0, Number(o.total_amount || 0) - Number(o.net_paid_amount || 0)) > 0
        );
        if (firstUnpaidValid) orderSelect.value = String(firstUnpaidValid.id);
    }

    updateSuggestedMatchAmount();

    const modalEl = document.getElementById("manualMatchModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

function updateSuggestedMatchAmount() {
    const txId = Number(document.getElementById("match-tx-id")?.value || 0);
    const orderSelect = document.getElementById("match-order-select");
    const orderId = Number(orderSelect?.value || 0);
    const orderGroup = document.getElementById("match-order-group") || orderSelect?.closest(".mb-3");
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

    // Nếu đơn hàng đã thu đủ (khách đã chuyển lại)
    if (!isCancelled && (isPaid || ordRem <= 0)) {
        // 1. Ẩn chỗ chọn hóa đơn nhận tiền
        if (orderGroup) {
            orderGroup.classList.add("d-none");
        }

        // 2. Ẩn phần số tiền chuyển thừa
        if (amountGroup) {
            amountGroup.classList.add("d-none");
        }
        if (amountInput) {
            amountInput.value = String(txUnalloc);
            amountInput.disabled = true;
        }

        // 3. Chỉ ghi: Hóa đơn (mã hóa đơn) đã được thanh toán đủ (khách đã chuyển lại), bỏ chú thích bên dưới
        if (noticeBox) {
            noticeBox.className = "alert alert-warning py-2 px-3 small mb-3 fw-semibold";
            noticeBox.textContent = `Hóa đơn ${ord.order_code} đã được thanh toán đủ (khách đã chuyển lại)`;
            noticeBox.classList.remove("d-none");
        }

        // 4. Nhãn & nội dung phương thức xử lý
        if (reasonLabel) {
            reasonLabel.innerHTML = 'Phương thức xử lý tiền thừa <span class="text-danger">*</span>';
        }
        if (reasonInput) {
            if (!reasonInput.value || reasonInput.value.includes("Khách hàng xác nhận chuyển khoản thanh toán")) {
                reasonInput.value = `Khách hàng đã chuyển lại thanh toán đơn ${ord.order_code}, khoản chuyển sai nội dung này đã được xử lý hoàn trả tiền thừa cho khách.`;
            }
            reasonInput.placeholder = "Ghi rõ phương thức xử lý khoản tiền thừa (ví dụ: Đã hoàn tiền mặt cho khách tại quầy, chuyển khoản lại...)...";
        }

        // 5. Đổi nút thành "Xác nhận" giống bên hộp thoại xử lý thừa tiền
        if (confirmBtn) {
            confirmBtn.textContent = "Xác nhận";
            confirmBtn.className = "btn-fp-success";
        }
    } else {
        // Trường hợp đơn hàng còn phải thu bình thường: hiện lại đầy đủ
        if (orderGroup) {
            orderGroup.classList.remove("d-none");
        }
        if (amountGroup) {
            amountGroup.classList.remove("d-none");
        }
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
}

// 5. Xử lý xác nhận Ghép tiền vào hóa đơn
// 5. Xử lý xác nhận Ghép tiền vào hóa đơn
async function handleManualMatchSubmit(event) {
    event.preventDefault();
    if (isSubmittingDecision) return;

    const bankTxId = Number(document.getElementById("match-tx-id")?.value || 0);
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
                    assertion_signature: webauthnProof.assertion_signature,
                    client_data_json: webauthnProof.client_data_json,
                    authenticator_data: webauthnProof.authenticator_data
                })
            });
        }
    } catch (error) {
        if (error.isNetworkError) {
            if (securityMode === "BYPASS_WEBAUTHN_TEST") {
                if (errorBox) {
                    errorBox.textContent = "401 Unauthorized: Từ chối thực hiện do không có chữ ký xác thực khóa bảo mật WebAuthn!";
                    errorBox.classList.remove("d-none");
                }
                showToast("Đã chặn yêu cầu chưa qua xác thực bảo mật (401)!", "danger");
                isSubmittingDecision = false;
                return;
            }

            const store = getDemoStore();
            const tx = store.bank_transactions.find((t) => Number(t.id) === bankTxId);
            const ord = store.orders.find((o) => Number(o.id) === orderId);

            if (!tx || !ord) {
                isSubmittingDecision = false;
                return;
            }

            if (String(ord.order_status).toUpperCase() === "CANCELLED_ORDER") {
                if (errorBox) {
                    errorBox.textContent = `Hóa đơn ${ord.order_code} đã bị hủy nên không thể phân bổ tiền.`;
                    errorBox.classList.remove("d-none");
                }
                showToast("Không thể ghép tiền vào hóa đơn đã hủy (400)!", "danger");
                isSubmittingDecision = false;
                return;
            }

            const ordRemaining = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));
            if (String(ord.payment_status).toUpperCase() === "PAID" || ordRemaining <= 0) {
                if (errorBox) {
                    errorBox.textContent = `Hóa đơn ${ord.order_code} đã thanh toán đủ nên không thể nhận thêm tiền.`;
                    errorBox.classList.remove("d-none");
                }
                showToast("Không thể ghép tiền vào hóa đơn đã thu đủ (400)!", "danger");
                isSubmittingDecision = false;
                return;
            }

            const allocAmt = Math.min(manualAmount, Number(tx.unallocated_amount || 0), ordRemaining);
            tx.allocated_amount = Number(tx.allocated_amount || 0) + allocAmt;
            tx.unallocated_amount = Number(tx.unallocated_amount || 0) - allocAmt;
            tx.match_status = tx.unallocated_amount === 0 ? "FULLY_ALLOCATED" : "PARTIALLY_ALLOCATED";

            ord.net_paid_amount = Number(ord.net_paid_amount || 0) + allocAmt;
            ord.payment_status = ord.net_paid_amount >= ord.total_amount ? "PAID" : "PARTIALLY_PAID";
            if (ord.payment_status === "PAID" && ord.qr_request) {
                ord.qr_request.status = "FULFILLED";
            }

            const prevHash =
                store.allocations.length > 0
                    ? store.allocations[store.allocations.length - 1].record_hash
                    : "0".repeat(64);
            const newAllocId = store.allocations.length + 1;

            store.allocations.push({
                id: newAllocId,
                bank_transaction_id: tx.id,
                reference_code: tx.reference_code,
                payment_request_id: 100 + ord.id,
                order_id: ord.id,
                order_code: ord.order_code,
                entry_type: "ALLOCATION",
                allocated_amount: allocAmt,
                reversal_of_id: null,
                allocation_mode: "MANUAL",
                prev_hash: prevHash,
                record_hash: `c73f9a1b2e4d6c8f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e${newAllocId}`,
                created_at: new Date().toISOString(),
                is_valid: true
            });

            store.decisions.unshift({
                id: Date.now(),
                order_id: ord.id,
                order_code: ord.order_code,
                bank_transaction_id: tx.id,
                reference_code: tx.reference_code,
                reviewer_id: getCurrentUserId(),
                decision_type: "APPROVE_MANUAL_MATCH",
                reason,
                biometric_verified: true,
                review_date: new Date().toISOString()
            });

            saveDemoStore(store);
        } else {
            if (errorBox) {
                errorBox.textContent = error.message;
                errorBox.classList.remove("d-none");
            }
            showToast(error.message || "Yêu cầu bị từ chối!", "danger");
            isSubmittingDecision = false;
            return;
        }
    }

    isSubmittingDecision = false;
    const modalEl = document.getElementById("manualMatchModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();

    const targetTx = reconBankTxs.find((t) => Number(t.id) === bankTxId);
    if (targetTx) {
        targetTx.is_handled = true;
    }
    // Các khoản đã xử lý sẽ không hiện ở tab chờ xử lý nữa
    renderUnmatchedTable();

    showToast("Đã ghép khoản tiền vào hóa đơn thành công!", "success");
    loadReconciliationWorkspace(false);
}

// 6. Mở hộp thoại Đảo giao dịch
function openReverseModal(allocId) {
    const alloc = reconAllocations.find((a) => Number(a.id) === Number(allocId));
    if (!alloc) return;

    document.getElementById("reverse-alloc-id").value = String(alloc.id);
    document.getElementById("reverse-alloc-label").textContent = `Bút toán #${alloc.id} (${alloc.reference_code} → Hóa đơn ${alloc.order_code})`;
    document.getElementById("reverse-alloc-amount").textContent = formatVND(alloc.allocated_amount);
    document.getElementById("reverse-error-box")?.classList.add("d-none");

    const modalEl = document.getElementById("reverseAllocModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

// 7. Xử lý xác nhận Đảo giao dịch
async function handleReverseAllocSubmit(event) {
    event.preventDefault();
    if (isSubmittingDecision) return;

    const allocationId = Number(document.getElementById("reverse-alloc-id")?.value || 0);
    const reason = (document.getElementById("reverse-reason-input")?.value || "").trim();
    const errorBox = document.getElementById("reverse-error-box");

    if (errorBox) errorBox.classList.add("d-none");

    if (!reason || reason.length < 5) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập rõ lý do đảo giao dịch.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    isSubmittingDecision = true;
    try {
        const webauthnProof = await requestWebAuthnAssertion({
            decision_type: "REVERSE_ALLOCATION",
            allocation_id: allocationId
        });

        await apiRequest("/decisions", {
            method: "POST",
            body: JSON.stringify({
                reviewer_id: getCurrentUserId(),
                decision_type: "REVERSE_ALLOCATION",
                reversal_of_id: allocationId,
                allocation_id: allocationId,
                reason,
                credential_id: webauthnProof.credential_id,
                challenge_used: webauthnProof.challenge_used,
                assertion_signature: webauthnProof.assertion_signature,
                client_data_json: webauthnProof.client_data_json,
                authenticator_data: webauthnProof.authenticator_data
            })
        });
    } catch (error) {
        if (error.isNetworkError) {
            const store = getDemoStore();
            const originAlloc = store.allocations.find((a) => Number(a.id) === allocationId);
            if (!originAlloc) {
                isSubmittingDecision = false;
                return;
            }

            const reverseAmount = -Math.abs(Number(originAlloc.allocated_amount || 0));
            const tx = store.bank_transactions.find((t) => Number(t.id) === Number(originAlloc.bank_transaction_id));
            const ord = store.orders.find((o) => Number(o.id) === Number(originAlloc.order_id));

            if (tx) {
                tx.allocated_amount = Math.max(0, Number(tx.allocated_amount || 0) + reverseAmount);
                tx.unallocated_amount = Number(tx.unallocated_amount || 0) + Math.abs(reverseAmount);
                tx.match_status = tx.allocated_amount === 0 ? "UNMATCHED" : "PARTIALLY_ALLOCATED";
            }

            if (ord) {
                ord.net_paid_amount = Math.max(0, Number(ord.net_paid_amount || 0) + reverseAmount);
                ord.payment_status =
                    ord.net_paid_amount === 0
                        ? "UNPAID"
                        : ord.net_paid_amount < ord.total_amount
                        ? "PARTIALLY_PAID"
                        : "PAID";
                if (ord.qr_request && ord.qr_request.status === "FULFILLED") {
                    ord.qr_request.status = "ACTIVE";
                }
            }

            const prevHash =
                store.allocations.length > 0
                    ? store.allocations[store.allocations.length - 1].record_hash
                    : "0".repeat(64);
            const newId = store.allocations.length + 1;

            store.allocations.push({
                id: newId,
                bank_transaction_id: originAlloc.bank_transaction_id,
                reference_code: originAlloc.reference_code,
                payment_request_id: originAlloc.payment_request_id,
                order_id: originAlloc.order_id,
                order_code: originAlloc.order_code,
                entry_type: "REVERSAL",
                allocated_amount: reverseAmount,
                reversal_of_id: originAlloc.id,
                allocation_mode: "MANUAL",
                prev_hash: prevHash,
                record_hash: `d94a8b7c6e5f4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d${newId}`,
                created_at: new Date().toISOString(),
                is_valid: true
            });

            store.decisions.unshift({
                id: Date.now(),
                order_id: originAlloc.order_id,
                order_code: originAlloc.order_code,
                bank_transaction_id: originAlloc.bank_transaction_id,
                reference_code: originAlloc.reference_code,
                reviewer_id: getCurrentUserId(),
                decision_type: "REVERSE_ALLOCATION",
                reason,
                biometric_verified: true,
                review_date: new Date().toISOString()
            });

            saveDemoStore(store);
        } else {
            if (errorBox) {
                errorBox.textContent = error.message;
                errorBox.classList.remove("d-none");
            }
            isSubmittingDecision = false;
            return;
        }
    }

    isSubmittingDecision = false;
    const modalEl = document.getElementById("reverseAllocModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
    showToast("Đã hoàn đảo giao dịch về danh sách chờ xử lý!", "success");
    loadReconciliationWorkspace(false);
}

function escapeReconHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}