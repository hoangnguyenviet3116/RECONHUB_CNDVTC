// ==========================================================================
// CỔNG THANH TOÁN NGÂN HÀNG MÔ PHỎNG (frontend/js/bank_simulator.js)
// ==========================================================================

let bankTxCache = [];
let simOrdersCache = [];
let isTriggeringTransfer = false;

function initBankSimulatorPage() {
    generateFreshReferenceCode();
    bindSimulatorEvents();
    loadOrdersForSimulatorSelect().then(() => {
        applyUrlQueryPrefill();
    });
    loadBankTransactionsList(false);
}

function generateFreshReferenceCode() {
    const refInput = document.getElementById("sim-reference-code");
    if (!refInput) return "";
    const randomSuffix = Math.floor(100000 + Math.random() * 900000);
    const code = `FT2629${randomSuffix}`;
    refInput.value = code;
    return code;
}

function applyUrlQueryPrefill() {
    const params = new URLSearchParams(window.location.search);
    const orderCode = params.get("order_code");
    const amount = params.get("amount");

    const orderSelect = document.getElementById("sim-order-select");
    const contentInput = document.getElementById("sim-transfer-content");
    const amountInput = document.getElementById("sim-amount");

    if (orderCode) {
        const cleanCode = orderCode.trim().toUpperCase();
        if (orderSelect) orderSelect.value = cleanCode;
        if (contentInput) contentInput.value = `TT ${cleanCode}`;
    }
    if (amount && amountInput && Number(amount) > 0) {
        amountInput.value = String(Math.round(Number(amount)));
    }
}

function bindSimulatorEvents() {
    document.getElementById("btn-gen-ref-code")?.addEventListener("click", () => {
        const newRef = generateFreshReferenceCode();
        showToast(`Mã giao dịch mới: ${newRef}`, "info");
    });

    const orderSelect = document.getElementById("sim-order-select");
    if (orderSelect) {
        orderSelect.addEventListener("change", (e) => {
            const selectedCode = e.target.value;
            if (!selectedCode) return;
            const found = simOrdersCache.find((o) => o.order_code === selectedCode);
            const contentInput = document.getElementById("sim-transfer-content");
            const amountInput = document.getElementById("sim-amount");

            if (contentInput) contentInput.value = `TT ${selectedCode}`;
            if (found && amountInput) {
                const remaining = Math.max(
                    0,
                    Number(found.total_amount || 0) - Number(found.net_paid_amount || found.allocated_amount || 0)
                );
                amountInput.value = String(remaining > 0 ? remaining : found.total_amount);
            }
            generateFreshReferenceCode();
        });
    }

    const scenarioBtns = document.querySelectorAll("[data-scenario]");
    scenarioBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            scenarioBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            applyTestScenarioPreset(btn.getAttribute("data-scenario"));
        });
    });

    document.getElementById("mock-bank-form")?.addEventListener("submit", handleTriggerTransferSubmit);
    document.getElementById("btn-refresh-bank-tx")?.addEventListener("click", () => loadBankTransactionsList(true));
}

function applyTestScenarioPreset(scenarioKey) {
    const amountInput = document.getElementById("sim-amount");
    const contentInput = document.getElementById("sim-transfer-content");
    const modeSelect = document.getElementById("sim-test-mode");
    const orderSelect = document.getElementById("sim-order-select");

    const selectedCode = orderSelect?.value;
    const targetOrder =
        simOrdersCache.find((o) => o.order_code === selectedCode) ||
        simOrdersCache.find((o) => String(o.payment_status).toUpperCase() !== "PAID") ||
        { order_code: "ORD1003", total_amount: 15000000, net_paid_amount: 0 };

    if (orderSelect && targetOrder.order_code) {
        orderSelect.value = targetOrder.order_code;
    }

    const remaining = Math.max(
        0,
        Number(targetOrder.total_amount || 15000000) - Number(targetOrder.net_paid_amount || 0)
    );
    const baseAmount = remaining > 0 ? remaining : Number(targetOrder.total_amount || 200000);

    generateFreshReferenceCode();
    if (modeSelect) modeSelect.value = "STANDARD";

    switch (scenarioKey) {
        case "TC02_EXACT":
            if (amountInput) amountInput.value = String(baseAmount);
            if (contentInput) contentInput.value = `TT ${targetOrder.order_code}`;
            break;
        case "TC03_PARTIAL":
            if (amountInput) amountInput.value = String(Math.max(10000, Math.round(baseAmount * 0.6)));
            if (contentInput) contentInput.value = `TT ${targetOrder.order_code}`;
            break;
        case "TC04_OVERPAID":
            if (amountInput) amountInput.value = String(baseAmount + 50000);
            if (contentInput) contentInput.value = `TT ${targetOrder.order_code}`;
            break;
        case "TC05_WRONG_CODE":
            if (amountInput) amountInput.value = String(baseAmount);
            if (contentInput) contentInput.value = "KHACH CHUYEN TIEN QUEN GHI MA DON";
            break;
        default:
            break;
    }
}

async function loadOrdersForSimulatorSelect() {
    const selectEl = document.getElementById("sim-order-select");
    if (!selectEl) return;

    try {
        const data = await apiRequest("/orders");
        simOrdersCache = Array.isArray(data) ? data : (data.items || data.orders || []);
    } catch (_) {
        simOrdersCache = getDemoStore().orders || [];
    }

    const unpaidOrders = simOrdersCache.filter((o) => String(o.payment_status).toUpperCase() !== "PAID");
    const listToShow = unpaidOrders.length > 0 ? unpaidOrders : simOrdersCache;

    const optionsHtml = listToShow
        .map((o) => {
            const rem = Math.max(
                0,
                Number(o.total_amount || 0) - Number(o.net_paid_amount || o.allocated_amount || 0)
            );
            return `<option value="${escapeSimHtml(o.order_code)}">
                Hóa đơn ${escapeSimHtml(o.order_code)} — Cần thu: ${formatVND(rem > 0 ? rem : o.total_amount)}
            </option>`;
        })
        .join("");

    selectEl.innerHTML = `<option value="">-- Tự nhập thông tin chuyển khoản --</option>` + optionsHtml;

    if (unpaidOrders.length > 0 && !selectEl.value) {
        selectEl.value = unpaidOrders[0].order_code;
        const rem = Math.max(0, Number(unpaidOrders[0].total_amount || 0) - Number(unpaidOrders[0].net_paid_amount || 0));
        document.getElementById("sim-transfer-content").value = `TT ${unpaidOrders[0].order_code}`;
        document.getElementById("sim-amount").value = String(rem > 0 ? rem : unpaidOrders[0].total_amount);
    }
}

async function loadBankTransactionsList(showNotification = false) {
    try {
        let data;
        try {
            data = await apiRequest("/bank-transactions");
        } catch (err) {
            if (err.status === 404) {
                const dash = await apiRequest("/dashboard/summary");
                data = dash.recent_bank_transactions || dash.bank_transactions || [];
            } else {
                throw err;
            }
        }
        bankTxCache = Array.isArray(data) ? data : (data.items || data.transactions || []);
    } catch (_) {
        bankTxCache = getDemoStore().bank_transactions || [];
    }

    renderBankTransactionsTable(bankTxCache);
    if (showNotification) {
        showToast("Đã cập nhật biến động số dư.", "success");
    }
}

function renderBankTransactionsTable(txs) {
    const tbody = document.getElementById("sim-bank-tx-tbody");
    if (!tbody) return;

    if (!txs || txs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-secondary">
                    Chưa có giao dịch chuyển khoản nào.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = txs
        .map((tx) => {
            const amount = Number(tx.amount || 0);
            const allocated = Number(tx.allocated_amount || 0);
            const unallocated = Number(tx.unallocated_amount ?? Math.max(0, amount - allocated));

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeSimHtml(tx.reference_code)}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(tx.created_at)}</div>
                    </td>
                    <td>
                        <span class="fw-medium text-dark">${escapeSimHtml(tx.transfer_content)}</span>
                    </td>
                    <td class="text-end fw-bold font-numeric">
                        ${formatVND(amount)}
                    </td>
                    <td class="text-end font-numeric">
                        <div class="text-success fw-semibold small">Khớp: ${formatVND(allocated)}</div>
                        ${
                            unallocated > 0
                                ? `<div class="text-danger fw-bold small">Dư: ${formatVND(unallocated)}</div>`
                                : `<div class="text-secondary small">Dư: 0 ₫</div>`
                        }
                    </td>
                    <td>
                        ${renderStatusBadge(tx.match_status || "UNMATCHED")}
                    </td>
                </tr>
            `;
        })
        .join("");
}

async function handleTriggerTransferSubmit(event) {
    event.preventDefault();
    if (isTriggeringTransfer) return;

    const referenceCode = (document.getElementById("sim-reference-code")?.value || "").trim().toUpperCase();
    const amount = Number(document.getElementById("sim-amount")?.value || 0);
    const transferContent = (document.getElementById("sim-transfer-content")?.value || "").trim();
    const testMode = document.getElementById("sim-test-mode")?.value || "STANDARD";
    const errorBox = document.getElementById("sim-form-error");
    const submitBtn = document.getElementById("btn-trigger-transfer");

    if (errorBox) errorBox.classList.add("d-none");

    if (!referenceCode || amount <= 0 || !transferContent) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập đầy đủ mã giao dịch, số tiền > 0 và nội dung chuyển khoản.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    isTriggeringTransfer = true;
    const oldHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Đang xử lý...`;
    }

    const basePayload = {
        merchant_id: getCurrentMerchantId(),
        reference_code: referenceCode,
        amount: amount,
        transfer_content: transferContent,
        tamper_signature: testMode === "INVALID_HMAC",
        simulate_invalid_hmac: testMode === "INVALID_HMAC"
    };

    try {
        if (testMode === "CONCURRENT_DUPLICATE") {
            await Promise.allSettled([
                apiRequest("/mock-bank/trigger-transfer", { method: "POST", body: JSON.stringify(basePayload) }),
                apiRequest("/mock-bank/trigger-transfer", { method: "POST", body: JSON.stringify(basePayload) })
            ]);
            renderFriendlyReceipt({
                badgeText: "Chặn trùng lặp",
                isSuccess: true,
                title: "Đã ngăn chặn cộng tiền trùng 2 lần",
                message: `Giao dịch ${referenceCode} bị gửi lặp 2 lần nhưng hệ thống chỉ ghi nhận đúng 1 lần duy nhất.`,
                referenceCode,
                amount,
                transferContent
            });
        } else {
            const response = await apiRequest("/mock-bank/trigger-transfer", {
                method: "POST",
                body: JSON.stringify(basePayload)
            });
            renderFriendlyReceipt({
                badgeText: "Thành công",
                isSuccess: true,
                title: "Chuyển khoản thành công",
                message: response.message || "Đã tiếp nhận khoản chuyển khoản và tự động đối soát với hóa đơn.",
                referenceCode,
                amount,
                transferContent
            });
        }

        generateFreshReferenceCode();
        await loadBankTransactionsList(false);
        await loadOrdersForSimulatorSelect();
    } catch (error) {
        if (error.isNetworkError) {
            executeStoreTransferSimulation(basePayload, testMode);
        } else {
            renderFriendlyReceipt({
                badgeText: "Bị từ chối",
                isSuccess: false,
                title: "Giao dịch bị từ chối bảo mật",
                message: error.message || "Thông báo chuyển khoản không hợp lệ.",
                referenceCode,
                amount,
                transferContent
            });
            showToast(error.message, "danger");
        }
    } finally {
        isTriggeringTransfer = false;
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = oldHtml;
        }
    }
}

function executeStoreTransferSimulation(payload, testMode) {
    if (testMode === "INVALID_HMAC") {
        renderFriendlyReceipt({
            badgeText: "Chặn bảo mật",
            isSuccess: false,
            title: "Đã chặn bản tin sai chữ ký xác thực",
            message: "Bản tin báo có không khớp chữ ký bảo mật của ngân hàng nên không được ghi nhận vào sổ quỹ.",
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content
        });
        showToast("Đã chặn bản tin sai chữ ký bảo mật!", "danger");
        return;
    }

    const store = getDemoStore();
    const exists = (store.bank_transactions || []).some((t) => t.reference_code === payload.reference_code);

    if (exists) {
        renderFriendlyReceipt({
            badgeText: "Đã chặn trùng",
            isSuccess: false,
            title: "Mã giao dịch này đã được xử lý trước đó",
            message: `Mã giao dịch ${payload.reference_code} đã tồn tại trong sổ quỹ, hệ thống từ chối cộng tiền lần 2.`,
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content
        });
        showToast("Đã chặn mã giao dịch trùng lặp!", "warning");
        return;
    }

    const match = payload.transfer_content.toUpperCase().match(/ORD\d+/);
    const matchedCode = match ? match[0] : null;
    const matchedOrder = matchedCode ? store.orders.find((o) => o.order_code === matchedCode) : null;

    let allocated = 0;
    let unallocated = payload.amount;
    let matchStatus = "UNMATCHED";
    let title = "Khoản tiền đã chuyển sang mục Đối soát lệch";
    let message = "Không tìm thấy mã hóa đơn hợp lệ trong nội dung chuyển khoản. Kế toán có thể ghép thủ công ở mục Đối soát lệch.";
    let nextLinkHtml = `<a href="reconciliation.html" class="btn-fp-dark py-1 px-3 mt-2" style="font-size:0.8rem;">Mở trang Đối soát lệch để ghép đơn →</a>`;

    if (matchedOrder && String(matchedOrder.payment_status).toUpperCase() !== "PAID") {
        const orderRem = Math.max(
            0,
            Number(matchedOrder.total_amount || 0) - Number(matchedOrder.net_paid_amount || 0)
        );
        allocated = Math.min(payload.amount, orderRem);
        unallocated = payload.amount - allocated;
        matchStatus = unallocated === 0 ? "FULLY_ALLOCATED" : "PARTIALLY_ALLOCATED";

        matchedOrder.net_paid_amount = Number(matchedOrder.net_paid_amount || 0) + allocated;
        matchedOrder.overpaid_amount = unallocated;
        matchedOrder.payment_status =
            matchedOrder.net_paid_amount >= matchedOrder.total_amount ? "PAID" : "PARTIALLY_PAID";

        if (matchedOrder.payment_status === "PAID" && matchedOrder.qr_request) {
            matchedOrder.qr_request.status = "FULFILLED";
        }

        // Ghi bút toán vào sổ cái chuỗi băm
        const prevHash =
            store.allocations.length > 0
                ? store.allocations[store.allocations.length - 1].record_hash
                : "0".repeat(64);
        const allocId = store.allocations.length + 1;

        store.allocations.push({
            id: allocId,
            bank_transaction_id: Date.now(),
            reference_code: payload.reference_code,
            payment_request_id: matchedOrder.qr_request?.id || 100 + matchedOrder.id,
            order_id: matchedOrder.id,
            order_code: matchedOrder.order_code,
            entry_type: "ALLOCATION",
            allocated_amount: allocated,
            reversal_of_id: null,
            allocation_mode: "AUTO",
            prev_hash: prevHash,
            record_hash: `a8f5e2c9d1b40768f12e34a56b78c90d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a${allocId}`,
            created_at: new Date().toISOString(),
            is_valid: true
        });

        if (unallocated > 0) {
            title = `Hóa đơn ${matchedOrder.order_code} đã thu đủ & tách riêng ${formatVND(unallocated)} tiền thừa`;
            message = `Hệ thống chỉ gạch nợ đúng ${formatVND(allocated)} cho hóa đơn ${matchedOrder.order_code}. Phần tiền thừa ${formatVND(unallocated)} được giữ lại để xử lý.`;
        } else if (matchedOrder.payment_status === "PAID") {
            title = `Hóa đơn ${matchedOrder.order_code} đã thanh toán hoàn tất!`;
            message = `Đã khớp tự động ${formatVND(allocated)} vào hóa đơn ${matchedOrder.order_code}.`;
        } else {
            const stillMissing = Math.max(0, matchedOrder.total_amount - matchedOrder.net_paid_amount);
            title = `Hóa đơn ${matchedOrder.order_code} vừa nhận ${formatVND(allocated)}`;
            message = `Khách chuyển thiếu. Hóa đơn còn cần thu thêm ${formatVND(stillMissing)}.`;
        }
        nextLinkHtml = `<a href="pos.html" class="btn-fp-outline py-1 px-3 mt-2" style="font-size:0.8rem;">← Quay lại Quầy thu ngân</a>`;
    }

    const newTx = {
        id: Date.now(),
        merchant_id: 1,
        reference_code: payload.reference_code,
        amount: payload.amount,
        allocated_amount: allocated,
        unallocated_amount: unallocated,
        transfer_content: payload.transfer_content,
        match_status: matchStatus,
        created_at: new Date().toISOString()
    };

    store.bank_transactions.unshift(newTx);
    saveDemoStore(store);

    bankTxCache = store.bank_transactions;
    simOrdersCache = store.orders;
    renderBankTransactionsTable(bankTxCache);
    loadOrdersForSimulatorSelect();

    renderFriendlyReceipt({
        badgeText: matchStatus === "UNMATCHED" ? "Chờ ghép đơn" : "Đã đối soát",
        isSuccess: true,
        title,
        message,
        referenceCode: payload.reference_code,
        amount: payload.amount,
        transferContent: payload.transfer_content,
        allocated,
        unallocated,
        nextLinkHtml
    });

    generateFreshReferenceCode();
    showToast(`Đã thực hiện chuyển khoản ${formatVND(payload.amount)}`, "success");
}

function renderFriendlyReceipt({
    badgeText,
    isSuccess,
    title,
    message,
    referenceCode,
    amount,
    transferContent,
    allocated,
    unallocated,
    nextLinkHtml = ""
}) {
    const statusBadge = document.getElementById("inspector-http-status");
    const boxEl = document.getElementById("inspector-friendly-box");

    if (statusBadge) {
        statusBadge.className = `fp-badge ${isSuccess ? "fp-badge-success" : "fp-badge-danger"}`;
        statusBadge.textContent = badgeText;
    }

    if (!boxEl) return;

    const splitRow =
        allocated !== undefined
            ? `<div class="d-flex justify-content-between pt-2 mt-2 border-top">
                   <span>Đã khớp đơn: <strong class="text-success font-numeric">${formatVND(allocated)}</strong></span>
                   <span>Còn dư / Chờ xử lý: <strong class="${unallocated > 0 ? "text-danger" : "text-secondary"} font-numeric">${formatVND(unallocated)}</strong></span>
               </div>`
            : "";

    boxEl.className = `p-3 rounded-3 border small ${isSuccess ? "bg-success-subtle border-success-subtle" : "bg-danger-subtle border-danger-subtle"}`;
    boxEl.innerHTML = `
        <div class="fw-bold ${isSuccess ? "text-success-emphasis" : "text-danger-emphasis"} mb-1">${escapeSimHtml(title)}</div>
        <div class="text-dark mb-2">${escapeSimHtml(message)}</div>
        <div class="p-2 px-3 rounded-3 bg-white border">
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Mã GD:</span>
                <strong class="font-numeric">${escapeSimHtml(referenceCode)}</strong>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Số tiền:</span>
                <strong class="font-numeric">${formatVND(amount)}</strong>
            </div>
            <div class="d-flex justify-content-between py-1">
                <span class="text-secondary">Nội dung:</span>
                <strong>${escapeSimHtml(transferContent)}</strong>
            </div>
            ${splitRow}
        </div>
        ${nextLinkHtml}
    `;
}

function escapeSimHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}