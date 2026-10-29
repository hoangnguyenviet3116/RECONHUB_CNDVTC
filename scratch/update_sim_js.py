# -*- coding: utf-8 -*-

with open("frontend/js/bank_simulator.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update initBankSimulatorPage to allow navigating from navbar
old_init = """function initBankSimulatorPage() {
    const params = new URLSearchParams(window.location.search);
    const orderCode = params.get("order_code");

    // Chỉ cho phép mở trang Cổng thanh toán khi người dùng bấm "Thanh toán đơn này" từ một hóa đơn
    if (!orderCode) {
        showToast("Vui lòng chọn hóa đơn và bấm 'Thanh toán đơn này' tại Quầy thu ngân.", "warning");
        setTimeout(() => {
            window.location.replace("pos.html");
        }, 600);
        return;
    }

    generateFreshReferenceCode();
    bindSimulatorEvents();
    loadOrdersForSimulatorSelect().then(() => {
        applyUrlQueryPrefill();
    });
    loadBankTransactionsList(false);
}"""

new_init = """function initBankSimulatorPage() {
    generateFreshReferenceCode();
    bindSimulatorEvents();
    loadOrdersForSimulatorSelect().then(() => {
        applyUrlQueryPrefill();
    });
    loadBankTransactionsList(false);
}"""

code = code.replace(old_init, new_init)

# 2. Add time helper
if "function formatTimeOnlyWithSeconds" not in code:
    code = """function formatTimeOnlyWithSeconds(dateStr) {
    if (!dateStr) return "--:--:--";
    const d = new Date(dateStr);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
""" + code

# 3. Add listener for sim-scenario-select in bindSimulatorEvents
scenario_listener = """    const scenarioSelect = document.getElementById("sim-scenario-select");
    if (scenarioSelect) {
        scenarioSelect.addEventListener("change", (e) => {
            applyTestScenarioPreset(e.target.value);
        });
    }
"""
if "sim-scenario-select" not in code:
    code = code.replace("function bindSimulatorEvents() {", "function bindSimulatorEvents() {\n" + scenario_listener)

# 4. Update renderBankTransactionsTable
old_table_fn = """function renderBankTransactionsTable(txs) {
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
}"""

new_table_fn = """function renderBankTransactionsTable(txs) {
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
}"""

code = code.replace(old_table_fn, new_table_fn)

# 5. Update renderFriendlyReceipt
old_receipt_fn = """function renderFriendlyReceipt({
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
                <span class="text-secondary">Thời gian chuyển khoản:</span>
                <strong class="font-numeric text-dark">${formatDateTime(transferTime || new Date())}</strong>
            </div>
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
}"""

new_receipt_fn = """function renderFriendlyReceipt({
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
}"""

code = code.replace(old_receipt_fn, new_receipt_fn)

with open("frontend/js/bank_simulator.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated frontend/js/bank_simulator.js successfully.")
