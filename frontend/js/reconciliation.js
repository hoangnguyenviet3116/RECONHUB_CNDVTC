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
    REJECT_TX: "Từ chối giao dịch"
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

        const store = getDemoStore();
        const orders = Array.isArray(ordersRes) ? ordersRes : (ordersRes.items || ordersRes.orders || []);
        reconOrders = orders.length > 0 ? orders : store.orders;
        reconBankTxs = summaryRes.bank_transactions || summaryRes.recent_bank_transactions || store.bank_transactions;
        reconAllocations = summaryRes.payment_allocations || summaryRes.ledger_entries || store.allocations;
        reconDecisions = summaryRes.decisions || summaryRes.recent_decisions || store.decisions;
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

// 1. Bảng các khoản tiền chờ ghép đơn
function renderUnmatchedTable() {
    const tbody = document.getElementById("recon-unmatched-tbody");
    const countBadge = document.getElementById("badge-unmatched-count");
    if (!tbody) return;

    const exceptionTxs = (reconBankTxs || []).filter(
        (tx) =>
            Number(tx.unallocated_amount || 0) > 0 ||
            String(tx.match_status || "").toUpperCase() === "UNMATCHED"
    );

    if (countBadge) {
        countBadge.textContent = String(exceptionTxs.length);
    }

    if (exceptionTxs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-success fw-medium">
                    ✓ Tất cả các khoản chuyển khoản đã được khớp vào hóa đơn (Không có khoản tiền lệch).
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = exceptionTxs
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
        .join("");
}

// 2. Bảng các khoản đã khớp & hoàn đảo
function renderAllocationsTable() {
    const tbody = document.getElementById("recon-allocations-tbody");
    if (!tbody) return;

    if (!reconAllocations || reconAllocations.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4 text-secondary">
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

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-dark">Bút toán #${alloc.id}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(alloc.created_at)}</div>
                    </td>
                    <td class="font-numeric fw-medium">
                        ${escapeReconHtml(alloc.reference_code || `GD #${alloc.bank_transaction_id}`)}
                    </td>
                    <td>
                        <strong>Hóa đơn ${escapeReconHtml(alloc.order_code || `#${alloc.order_id}`)}</strong>
                    </td>
                    <td>
                        ${renderStatusBadge(isReversal ? "REVERSAL" : "ALLOCATION")}
                    </td>
                    <td class="text-end fw-bold font-numeric ${isReversal ? "text-danger" : "text-success"}">
                        ${amount > 0 ? `+${formatVND(amount)}` : formatVND(amount)}
                    </td>
                    <td class="text-end">
                        ${
                            isReversal
                                ? `<span class="small text-secondary">Bút toán đảo</span>`
                                : alreadyReversed
                                ? `<span class="fp-badge fp-badge-neutral">Đã hoàn đảo</span>`
                                : `<button type="button" class="btn-fp-outline py-1 px-3" style="font-size: 0.78rem;" onclick="openReverseModal(${alloc.id})">
                                       Đảo giao dịch
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}

// 3. Lịch sử phê duyệt
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
}

// 4. Mở hộp thoại Ghép tiền vào hóa đơn
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
                const rem = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));
                const statusLabel = rem === 0 ? "Đã thu đủ" : `Còn thiếu: ${formatVND(rem)}`;
                return `<option value="${ord.id}">Hóa đơn ${escapeReconHtml(ord.order_code)} — ${statusLabel}</option>`;
            })
            .join("");

        const firstUnpaid = reconOrders.find(
            (o) => Math.max(0, Number(o.total_amount || 0) - Number(o.net_paid_amount || 0)) > 0
        );
        if (firstUnpaid) orderSelect.value = String(firstUnpaid.id);
    }

    updateSuggestedMatchAmount();

    const modalEl = document.getElementById("manualMatchModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

function updateSuggestedMatchAmount() {
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
}

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
            errorBox.textContent = "Vui lòng nhập rõ lý do xác nhận.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    if (securityMode === "BYPASS_WEBAUTHN_TEST") {
        if (errorBox) {
            errorBox.textContent = "Từ chối thực hiện: Bắt buộc phải xác nhận bằng khóa bảo mật thiết bị trước khi ghép tiền.";
            errorBox.classList.remove("d-none");
        }
        showToast("Đã chặn yêu cầu chưa qua xác thực bảo mật!", "danger");
        return;
    }

    isSubmittingDecision = true;
    try {
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
                credential_id: webauthnProof.credential_id,
                challenge_used: webauthnProof.challenge_used,
                assertion_signature: webauthnProof.assertion_signature
            })
        });
    } catch (error) {
        if (error.isNetworkError) {
            const store = getDemoStore();
            const tx = store.bank_transactions.find((t) => Number(t.id) === bankTxId);
            const ord = store.orders.find((o) => Number(o.id) === orderId);

            if (!tx || !ord) {
                isSubmittingDecision = false;
                return;
            }

            const ordRemaining = Math.max(0, Number(ord.total_amount || 0) - Number(ord.net_paid_amount || 0));
            if (String(ord.payment_status).toUpperCase() === "PAID" || ordRemaining <= 0) {
                if (errorBox) {
                    errorBox.textContent = `Hóa đơn ${ord.order_code} đã thanh toán đủ nên không thể nhận thêm tiền.`;
                    errorBox.classList.remove("d-none");
                }
                showToast("Không thể ghép tiền vào hóa đơn đã thu đủ!", "danger");
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
            isSubmittingDecision = false;
            return;
        }
    }

    isSubmittingDecision = false;
    const modalEl = document.getElementById("manualMatchModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
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
                assertion_signature: webauthnProof.assertion_signature
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
    showToast("Đã hoàn đảo giao dịch về danh sách chờ ghép đơn!", "success");
    loadReconciliationWorkspace(false);
}

function escapeReconHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}