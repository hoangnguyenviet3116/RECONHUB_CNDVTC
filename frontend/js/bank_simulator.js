function formatTimeOnlyWithSeconds(dateStr) {
    if (!dateStr) return "--:--:--";
    const d = new Date(dateStr);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
// ==========================================================================
// CỔNG THANH TOÁN NGÂN HÀNG MÔ PHỎNG (frontend/js/bank_simulator.js)
// Chỉ hiển thị khi bấm "Thanh toán đơn này" từ hóa đơn và tự động quay về trang trước
// ==========================================================================

let bankTxCache = [];
let simOrdersCache = [];
let isTriggeringTransfer = false;

function getReturnUrl() {
    const params = new URLSearchParams(window.location.search);
    const returnUrl = params.get("return_url");
    if (returnUrl) return returnUrl;
    if (document.referrer && document.referrer.includes(".html") && !document.referrer.includes("bank-simulator.html")) {
        return document.referrer;
    }
    return "pos.html";
}

function redirectBackToPreviousPage(delayMs = 1200) {
    const targetUrl = getReturnUrl();
    setTimeout(() => {
        window.location.href = targetUrl;
    }, delayMs);
}

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
    const scenarioSelect = document.getElementById("sim-scenario-select");
    if (scenarioSelect) {
        scenarioSelect.addEventListener("change", (e) => {
            applyTestScenarioPreset(e.target.value);
        });
    }

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

    const params = new URLSearchParams(window.location.search);
    const urlOrderCode = params.get("order_code")?.trim().toUpperCase();
    const selectedCode = orderSelect?.value || urlOrderCode;

    const validOrders = simOrdersCache.filter(
        (o) => String(o.order_status).toUpperCase() !== "CANCELLED_ORDER"
    );
    const targetOrder =
        simOrdersCache.find((o) => o.order_code === selectedCode) ||
        validOrders.find((o) => String(o.payment_status).toUpperCase() !== "PAID") ||
        (validOrders.length > 0 ? validOrders[0] : null);

    if (targetOrder && orderSelect && targetOrder.order_code) {
        orderSelect.value = targetOrder.order_code;
    }

    const targetCode = targetOrder?.order_code || urlOrderCode || "ORD1001";
    const remaining = targetOrder
        ? Math.max(0, Number(targetOrder.total_amount || 0) - Number(targetOrder.net_paid_amount || 0))
        : 0;
    const baseAmount = targetOrder
        ? (remaining > 0 ? remaining : Number(targetOrder.total_amount || 200000))
        : Number(params.get("amount") || 200000);

    generateFreshReferenceCode();
    if (modeSelect) modeSelect.value = "STANDARD";

    switch (scenarioKey) {
        case "TC02_EXACT":
            if (amountInput) amountInput.value = String(baseAmount);
            if (contentInput) contentInput.value = `TT ${targetCode}`;
            break;
        case "TC03_PARTIAL":
            if (amountInput) amountInput.value = String(Math.max(10000, Math.round(baseAmount * 0.6)));
            if (contentInput) contentInput.value = `TT ${targetCode}`;
            break;
        case "TC04_OVERPAID":
            if (amountInput) amountInput.value = String(baseAmount + 50000);
            if (contentInput) contentInput.value = `TT ${targetCode}`;
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

    const unpaidValidOrders = simOrdersCache.filter(
        (o) =>
            String(o.payment_status).toUpperCase() !== "PAID" &&
            String(o.order_status).toUpperCase() !== "CANCELLED_ORDER"
    );
    const listToShow = unpaidValidOrders.length > 0 ? unpaidValidOrders : simOrdersCache;

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
}

async function loadBankTransactionsList(showNotification = false) {
    try {
        let data;
        try {
            data = await apiRequest("/mock-bank/transactions");
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
                <td colspan="5" class="text-center py-5 text-secondary">
                    Chưa có giao dịch chuyển khoản nào.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = txs
        .map((tx) => {
            const amount = Number(tx.amount || 0);
            const status = String(tx.match_status || "").toUpperCase();

            let statusPill = `<span class="pos-status-pill pos-status-cancelled">Chờ xử lý</span>`;
            if (status === "FULLY_ALLOCATED" || status === "ALLOCATION") {
                statusPill = `<span class="pos-status-pill pos-status-paid">Đã khớp đơn</span>`;
            } else if (status === "PARTIALLY_ALLOCATED") {
                statusPill = `<span class="pos-status-pill pos-status-partial">Thu một phần</span>`;
            }

            return `
                <tr>
                    <td>
                        <span class="text-secondary font-numeric" style="font-size: 0.86rem;">
                            ${formatTimeOnlyWithSeconds(tx.created_at)}
                        </span>
                    </td>
                    <td>
                        <span class="fw-bold text-dark font-numeric" style="font-size: 0.92rem;">
                            ${escapeSimHtml(tx.reference_code)}
                        </span>
                    </td>
                    <td>
                        <span class="fw-semibold text-dark">${escapeSimHtml(tx.transfer_content)}</span>
                    </td>
                    <td>
                        <span class="sim-amount-pos font-numeric">+${formatVND(amount)}</span>
                    </td>
                    <td class="text-end">
                        ${statusPill}
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

    const transferTime = new Date();
    const basePayload = {
        merchant_id: getCurrentMerchantId(),
        reference_code: referenceCode,
        amount: amount,
        transfer_content: transferContent,
        transfer_time: transferTime.toISOString(),
        transaction_date: transferTime.toISOString(),
        tamper_signature: testMode === "INVALID_HMAC",
        simulate_invalid_hmac: testMode === "INVALID_HMAC",
        test_mode: testMode,
        simulate_replay_attack: testMode === "REPLAY_ATTACK"
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
                transferContent,
                transferTime
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
                message: `${response.message || "Đã tiếp nhận khoản chuyển khoản và tự động đối soát."}`,
                referenceCode,
                amount,
                transferContent,
                transferTime
            });
        }

        // Lưu lại mã hóa đơn vừa chuyển khoản để trang Quầy thu ngân (pos.html) phát loa thông báo ngay khi quay về
        const match = transferContent.toUpperCase().match(/ORD[A-Z0-9_-]*/);
        if (match) {
            sessionStorage.setItem("recon_just_paid_order", match[0]);
        }

        showToast("Chuyển khoản thành công!", "success");
        redirectBackToPreviousPage(1200);
    } catch (error) {
        if (error.isNetworkError) {
            executeStoreTransferSimulation(basePayload, testMode, transferTime);
        } else {
            renderFriendlyReceipt({
                badgeText: "Bị từ chối",
                isSuccess: false,
                title: "Giao dịch bị từ chối bảo mật",
                message: error.message || "Thông báo chuyển khoản không hợp lệ.",
                referenceCode,
                amount,
                transferContent,
                transferTime
            });
            showToast(error.message, "danger");
            isTriggeringTransfer = false;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = oldHtml;
            }
        }
    }
}

function executeStoreTransferSimulation(payload, testMode, transferTime = null) {
    if (testMode === "INVALID_HMAC") {
        renderFriendlyReceipt({
            badgeText: "Chặn bảo mật",
            isSuccess: false,
            title: "Đã chặn bản tin sai chữ ký xác thực",
            message: "Bản tin báo có không khớp chữ ký bảo mật của ngân hàng nên không được ghi nhận vào sổ quỹ.",
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content,
            transferTime
        });
        showToast("Đã chặn bản tin sai chữ ký bảo mật!", "danger");
        isTriggeringTransfer = false;
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
            transferContent: payload.transfer_content,
            transferTime
        });
        showToast("Đã chặn mã giao dịch trùng lặp!", "warning");
        isTriggeringTransfer = false;
        return;
    }

    const match = payload.transfer_content.toUpperCase().match(/ORD[A-Z0-9_-]*/);
    const matchedCode = match ? match[0] : null;
    const matchedOrder = matchedCode ? store.orders.find((o) => o.order_code === matchedCode) : null;

    let allocated = 0;
    let unallocated = payload.amount;
    let matchStatus = "UNMATCHED";
    let title = "Khoản tiền đã chuyển sang mục Đối soát lệch";
    let message = "Không tìm thấy mã hóa đơn hợp lệ.";

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
            created_at: (transferTime || new Date()).toISOString(),
            is_valid: true
        });

        sessionStorage.setItem("recon_just_paid_order", matchedOrder.order_code);
        title = `Hóa đơn ${matchedOrder.order_code} đã ghi nhận thanh toán!`;
        message = `Đã đối soát ${formatVND(allocated)} cho hóa đơn ${matchedOrder.order_code}.`;
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
        created_at: (transferTime || new Date()).toISOString()
    };

    store.bank_transactions.unshift(newTx);
    saveDemoStore(store);

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
        transferTime
    });

    showToast("Chuyển khoản thành công!", "success");
    redirectBackToPreviousPage(1200);
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
    nextLinkHtml = "",
    transferTime = null
}) {
    const statusBadge = document.getElementById("inspector-http-status");
    const boxEl = document.getElementById("inspector-friendly-box");

    if (statusBadge) {
        statusBadge.className = `pos-status-pill ${isSuccess ? "pos-status-paid" : "pos-status-cancelled"}`;
        statusBadge.textContent = badgeText || (isSuccess ? "Thành công" : "Bị từ chối");
    }

    if (!boxEl) return;

    const splitRow =
        allocated !== undefined
            ? `<div class="d-flex justify-content-between pt-2 mt-2 border-top small">
                   <span>Đã khớp đơn: <strong class="text-success font-numeric">${formatVND(allocated)}</strong></span>
                   <span>Còn dư / Chờ xử lý: <strong class="${unallocated > 0 ? "text-danger" : "text-secondary"} font-numeric">${formatVND(unallocated)}</strong></span>
               </div>`
            : "";

    boxEl.className = "flex-grow-1 d-flex flex-column justify-content-start";
    boxEl.innerHTML = `
        <div class="p-3 rounded-4 border ${isSuccess ? "bg-success-subtle border-success-subtle" : "bg-danger-subtle border-danger-subtle"}">
            <div class="fw-bold ${isSuccess ? "text-success-emphasis" : "text-danger-emphasis"} mb-1" style="font-size: 1.05rem;">${escapeSimHtml(title)}</div>
            <div class="text-dark small mb-3">${escapeSimHtml(message)}</div>
            <div class="p-3 rounded-3 bg-white border">
                <div class="d-flex justify-content-between py-1.5 border-bottom small">
                    <span class="text-secondary">Thời gian chuyển khoản:</span>
                    <strong class="font-numeric text-dark">${formatDateTime(transferTime || new Date())}</strong>
                </div>
                <div class="d-flex justify-content-between py-1.5 border-bottom small">
                    <span class="text-secondary">Mã GD:</span>
                    <strong class="font-numeric text-dark">${escapeSimHtml(referenceCode)}</strong>
                </div>
                <div class="d-flex justify-content-between py-1.5 border-bottom small">
                    <span class="text-secondary">Số tiền:</span>
                    <strong class="font-numeric text-success fs-6">${formatVND(amount)}</strong>
                </div>
                <div class="d-flex justify-content-between py-1.5 small">
                    <span class="text-secondary">Nội dung:</span>
                    <strong class="text-dark">${escapeSimHtml(transferContent)}</strong>
                </div>
                ${splitRow}
            </div>
            ${nextLinkHtml}
        </div>
    `;
}

function escapeSimHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}