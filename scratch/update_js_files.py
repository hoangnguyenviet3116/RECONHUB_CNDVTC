# -*- coding: utf-8 -*-
"""
Update dashboard.js and pos.js to guarantee 100% synchronization between POS and Dashboard.
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')

# =========================================================================
# 1. READ AND UPDATE frontend/js/dashboard.js
# =========================================================================
with open("frontend/js/dashboard.js", "r", encoding="utf-8") as f:
    dash_js = f.read()

# Replace bindDashboardEvents and loadDashboardData
old_load_block = """async function loadDashboardData(showNotification = false) {
    let summaryData = null;

    try {
        summaryData = await apiRequest("/dashboard/summary");
    } catch (_) {
        const store = getDemoStore();
        summaryData = computeStoreSummary(store);
    }

    currentLedgerEntries = JSON.parse(JSON.stringify(summaryData.ledger_entries || []));
    renderDashboardKpisAndTables(summaryData);
    renderDashboardCharts(summaryData);
    renderHashChainVerificationResult({
        is_valid: true,
        total_records: currentLedgerEntries.length,
        tampered_block_id: null,
        entries: currentLedgerEntries
    });

    if (showNotification) {
        showToast("Đã cập nhật số liệu báo cáo mới nhất.", "success");
    }
}"""

new_load_block = """let isDashboardShiftPopulated = false;

function updateDashboardShiftDropdown(shifts, currentShiftId) {
    const filterEl = document.getElementById("dash-shift-filter");
    if (!filterEl || !Array.isArray(shifts) || shifts.length === 0) return;

    const curVal = filterEl.value;
    if (!isDashboardShiftPopulated || filterEl.options.length <= 2) {
        let html = '<option value="ALL">Tất cả ca bán hàng</option>';
        shifts.forEach((s) => {
            const statusLabel = String(s.status).toUpperCase() === "OPEN" ? "(Đang mở)" : "(Đã đóng)";
            html += `<option value="${s.id}">Ca ${s.id}: ${escapeDashHtml(s.name)} ${statusLabel}</option>`;
        });
        filterEl.innerHTML = html;
        isDashboardShiftPopulated = true;
    }

    if (curVal && Array.from(filterEl.options).some(o => o.value === curVal)) {
        filterEl.value = curVal;
    } else if (currentShiftId !== undefined && currentShiftId !== null) {
        filterEl.value = String(currentShiftId);
    }
}

async function loadDashboardData(showNotification = false) {
    let summaryData = null;
    const filterEl = document.getElementById("dash-shift-filter");
    const selectedShift = filterEl ? filterEl.value : "1";
    const query = selectedShift ? `?shift_id=${encodeURIComponent(selectedShift)}` : "";

    try {
        summaryData = await apiRequest(`/dashboard/summary${query}`);
    } catch (_) {
        const store = getDemoStore();
        summaryData = computeStoreSummary(store, selectedShift);
    }

    if (summaryData.available_shifts && Array.isArray(summaryData.available_shifts)) {
        updateDashboardShiftDropdown(summaryData.available_shifts, summaryData.shift_id);
    }

    currentLedgerEntries = JSON.parse(JSON.stringify(summaryData.ledger_entries || []));
    renderDashboardKpisAndTables(summaryData);
    renderDashboardOrdersTable(summaryData.orders || []);
    renderDashboardCharts(summaryData);
    renderHashChainVerificationResult({
        is_valid: Boolean(summaryData.ledger_integrity_valid ?? true),
        total_records: currentLedgerEntries.length,
        tampered_block_id: null,
        entries: currentLedgerEntries
    });

    if (showNotification) {
        showToast("Đã cập nhật số liệu báo cáo mới nhất.", "success");
    }
}"""

dash_js = dash_js.replace(old_load_block, new_load_block)

# Update renderDashboardKpisAndTables to set valid_order_count and cancelled_order_total
old_kpi_render = """    setText("kpi-remaining-receivable", formatVND(remaining));

    const formulaTbody = document.getElementById("dash-reconciliation-formula-tbody");"""

new_kpi_render = """    setText("kpi-remaining-receivable", formatVND(remaining));

    // Cập nhật số lượng đơn hợp lệ và đơn hủy
    const validCount = Number(data.valid_order_count ?? (data.orders ? data.orders.filter(o => o.order_status !== "CANCELLED_ORDER").length : 0));
    setText("dash-valid-order-count", `${validCount} đơn`);

    const cancelledTotal = Number(data.cancelled_order_total ?? 0);
    const cancelledCount = Number(data.cancelled_order_count ?? (data.orders ? data.orders.filter(o => o.order_status === "CANCELLED_ORDER").length : 0));
    const cancelledRow = document.getElementById("dash-cancelled-order-row");
    if (cancelledRow) {
        if (cancelledCount > 0 || cancelledTotal > 0) {
            cancelledRow.classList.remove("d-none");
            setText("dash-cancelled-order-total", `${formatVND(cancelledTotal)} (${cancelledCount} đơn)`);
        } else {
            cancelledRow.classList.add("d-none");
        }
    }

    const formulaTbody = document.getElementById("dash-reconciliation-formula-tbody");"""

dash_js = dash_js.replace(old_kpi_render, new_kpi_render)

# Add renderDashboardOrdersTable at bottom of file
orders_table_func = """
function renderDashboardOrdersTable(orders) {
    const tbody = document.getElementById("dash-orders-table-tbody");
    const countBadge = document.getElementById("dash-orders-count-badge");
    if (!tbody) return;

    if (!orders || orders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4 text-secondary">
                    Chưa có hóa đơn nào trong phạm vi ca được chọn.
                </td>
            </tr>
        `;
        if (countBadge) countBadge.textContent = "0 đơn";
        return;
    }

    if (countBadge) countBadge.textContent = `${orders.length} đơn`;

    tbody.innerHTML = orders
        .map((ord) => {
            const total = Number(ord.total_amount || 0);
            const paid = Number(
                ord.net_paid_amount ??
                ord.allocated_amount ??
                (String(ord.payment_status).toUpperCase() === "PAID" ? total : 0)
            );
            const remaining = Math.max(0, total - paid);
            const isCancelled = String(ord.order_status).toUpperCase() === "CANCELLED_ORDER";

            return `
                <tr class="${isCancelled ? "table-light text-muted" : ""}">
                    <td>
                        <strong class="${isCancelled ? "text-muted text-decoration-line-through" : "text-dark"}">${escapeDashHtml(ord.order_code)}</strong>
                        <div class="small text-secondary" style="font-size: 0.74rem;">${escapeDashHtml(ord.note || "—")}</div>
                    </td>
                    <td>
                        <span class="badge bg-light text-secondary border">Ca ${ord.shift_id}</span>
                    </td>
                    <td class="text-end fw-bold font-numeric">
                        ${isCancelled ? `<span class="text-decoration-line-through text-muted">${formatVND(total)}</span>` : formatVND(total)}
                    </td>
                    <td class="text-end font-numeric text-success fw-semibold">
                        ${formatVND(paid)}
                    </td>
                    <td class="text-end font-numeric ${remaining > 0 && !isCancelled ? "text-warning fw-semibold" : "text-secondary"}">
                        ${isCancelled ? "0 ₫" : formatVND(remaining)}
                    </td>
                    <td>
                        ${renderStatusBadge(ord.order_status)}
                    </td>
                    <td>
                        ${renderStatusBadge(ord.payment_status)}
                    </td>
                    <td>
                        ${
                            isCancelled
                                ? `<span class="fp-badge fp-badge-danger" title="Hóa đơn đã hủy theo kế toán không hạch toán vào sổ quỹ thu tiền">✕ Loại trừ khỏi sổ quỹ</span>`
                                : `<span class="fp-badge fp-badge-success" title="Tính 100% vào sổ quỹ">✓ Hạch toán sổ quỹ</span>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}
"""

dash_js += orders_table_func

with open("frontend/js/dashboard.js", "w", encoding="utf-8") as f:
    f.write(dash_js)
print("Updated frontend/js/dashboard.js successfully.")

# =========================================================================
# 2. READ AND UPDATE frontend/js/pos.js
# =========================================================================
with open("frontend/js/pos.js", "r", encoding="utf-8") as f:
    pos_js = f.read()

# In bindPosEvents, add change listener for pos-filter-shift
old_bind_events = """    const filterSelect = document.getElementById("pos-filter-payment");
    if (filterSelect) {
        filterSelect.addEventListener("change", () => renderPosOrdersTable(posOrdersCache));
    }"""

new_bind_events = """    const shiftFilterSelect = document.getElementById("pos-filter-shift");
    if (shiftFilterSelect) {
        shiftFilterSelect.addEventListener("change", (e) => {
            const formShiftSelect = document.getElementById("pos-shift-select");
            if (formShiftSelect && e.target.value !== "ALL") {
                formShiftSelect.value = e.target.value;
            }
            renderPosOrdersTable(posOrdersCache);
        });
    }

    const filterSelect = document.getElementById("pos-filter-payment");
    if (filterSelect) {
        filterSelect.addEventListener("change", () => renderPosOrdersTable(posOrdersCache));
    }"""

pos_js = pos_js.replace(old_bind_events, new_bind_events)

# Update loadOpenShiftsForPos to populate both pos-shift-select and pos-filter-shift
old_load_shifts = """// 3. Tải danh sách ca đang mở bán
async function loadOpenShiftsForPos() {
    const selectEl = document.getElementById("pos-shift-select");
    if (!selectEl) return;

    const urlParams = new URLSearchParams(window.location.search);
    const preferredShiftId = urlParams.get("shift_id");

    let shifts = [];
    try {
        const data = await apiRequest("/shifts");
        shifts = Array.isArray(data) ? data : (data.items || data.shifts || []);
    } catch (_) {
        shifts = getDemoStore().shifts || [];
    }

    const openShifts = shifts.filter((s) => String(s.status || "").toUpperCase() === "OPEN");
    if (openShifts.length > 0) {
        selectEl.innerHTML = openShifts
            .map(
                (s) =>
                    `<option value="${s.id}" ${String(s.id) === String(preferredShiftId) ? "selected" : ""}>
                        ${escapePosHtml(s.name)}
                    </option>`
            )
            .join("");
    }
}"""

new_load_shifts = """// 3. Tải danh sách ca đang mở bán và đồng bộ bộ lọc ca
async function loadOpenShiftsForPos() {
    const selectEl = document.getElementById("pos-shift-select");
    const filterShiftEl = document.getElementById("pos-filter-shift");

    const urlParams = new URLSearchParams(window.location.search);
    const preferredShiftId = urlParams.get("shift_id");

    let shifts = [];
    try {
        const data = await apiRequest("/shifts");
        shifts = Array.isArray(data) ? data : (data.items || data.shifts || []);
    } catch (_) {
        shifts = getDemoStore().shifts || [];
    }

    const openShifts = shifts.filter((s) => String(s.status || "").toUpperCase() === "OPEN");
    if (selectEl && openShifts.length > 0) {
        selectEl.innerHTML = openShifts
            .map(
                (s) =>
                    `<option value="${s.id}" ${String(s.id) === String(preferredShiftId) ? "selected" : ""}>
                        ${escapePosHtml(s.name)}
                    </option>`
            )
            .join("");
    }

    if (filterShiftEl && shifts.length > 0) {
        const defaultSelectedShift = preferredShiftId || (openShifts[0] ? String(openShifts[0].id) : "1");
        let html = '<option value="ALL">Tất cả ca bán hàng</option>';
        shifts.forEach((s) => {
            const statusLabel = String(s.status).toUpperCase() === "OPEN" ? "(Đang mở)" : "(Đã đóng)";
            const isSelected = String(s.id) === defaultSelectedShift ? "selected" : "";
            html += `<option value="${s.id}" ${isSelected}>Ca ${s.id}: ${escapePosHtml(s.name)} ${statusLabel}</option>`;
        });
        filterShiftEl.innerHTML = html;
    }
}"""

pos_js = pos_js.replace(old_load_shifts, new_load_shifts)

# Update renderPosOrdersTable to filter by shift, calculate summary bar statistics, and handle CANCELLED_ORDER
old_render_pos_table = """// 6. Hiển thị bảng danh sách hóa đơn trong ca
function renderPosOrdersTable(orders) {
    const tbody = document.getElementById("pos-orders-tbody");
    if (!tbody) return;

    const filterVal = document.getElementById("pos-filter-payment")?.value || "ALL";
    const searchVal = (document.getElementById("pos-search-order")?.value || "").trim().toUpperCase();

    const filtered = (orders || []).filter((ord) => {
        const payStatus = String(ord.payment_status || "UNPAID").toUpperCase();
        const code = String(ord.order_code || "").toUpperCase();
        const matchStatus = filterVal === "ALL" || payStatus === filterVal;
        const matchSearch = !searchVal || code.includes(searchVal);
        return matchStatus && matchSearch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-secondary">
                    Chưa có hóa đơn nào phù hợp.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered
        .map((ord) => {
            const total = Number(ord.total_amount || 0);
            const paid = Number(
                ord.net_paid_amount ??
                ord.allocated_amount ??
                (String(ord.payment_status).toUpperCase() === "PAID" ? total : 0)
            );
            const remaining = Math.max(0, total - paid);
            const qrObj = ord.qr_request || ord.active_payment_request || null;
            const qrStatus = qrObj ? qrObj.status : (ord.qr_status || "UNISSUED");
            const isPaid = String(ord.payment_status || "").toUpperCase() === "PAID";

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-dark">${escapePosHtml(ord.order_code)}</div>
                        <div class="text-secondary" style="font-size: 0.74rem;">
                            ${escapePosHtml(ord.note || formatDateTime(ord.created_at))}
                        </div>
                    </td>
                    <td class="text-end fw-bold font-numeric">
                        ${formatVND(total)}
                    </td>
                    <td class="text-end font-numeric">
                        <div class="fw-semibold text-success">${formatVND(paid)}</div>
                        ${
                            remaining > 0
                                ? `<div class="text-warning small" style="font-size: 0.74rem;">Còn thiếu: <strong>${formatVND(remaining)}</strong></div>`
                                : `<div class="text-secondary small" style="font-size: 0.74rem;">Hoàn tất</div>`
                        }
                    </td>
                    <td>
                        <div class="d-flex flex-column align-items-start gap-1">
                            ${renderStatusBadge(ord.payment_status || "UNPAID")}
                        </div>
                    </td>
                    <td class="text-end">
                        ${
                            isPaid
                                ? `<button type="button" class="btn-fp-outline py-1 px-3" style="font-size: 0.78rem;" onclick="openOrderQrModal(${ord.id}, false)">
                                       Xem biên lai
                                   </button>`
                                : `<button type="button" class="btn-fp-dark py-1 px-3" style="font-size: 0.78rem;" onclick="openOrderQrModal(${ord.id}, true)">
                                       ${getHeroicon("qr-code", "hi-icon hi-icon-sm")}
                                       <span>${qrStatus === "ACTIVE" ? "Hiện mã QR" : "Xuất mã QR"}</span>
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}"""

new_render_pos_table = """// 6. Hiển thị bảng danh sách hóa đơn và đồng bộ số liệu đối soát sổ quỹ
function renderPosOrdersTable(orders) {
    const tbody = document.getElementById("pos-orders-tbody");
    if (!tbody) return;

    const shiftFilterVal = document.getElementById("pos-filter-shift")?.value || "1";
    const filterVal = document.getElementById("pos-filter-payment")?.value || "ALL";
    const searchVal = (document.getElementById("pos-search-order")?.value || "").trim().toUpperCase();

    const filtered = (orders || []).filter((ord) => {
        const payStatus = String(ord.payment_status || "UNPAID").toUpperCase();
        const code = String(ord.order_code || "").toUpperCase();
        const matchShift = shiftFilterVal === "ALL" || String(ord.shift_id) === String(shiftFilterVal);
        const matchStatus = filterVal === "ALL" || payStatus === filterVal;
        const matchSearch = !searchVal || code.includes(searchVal);
        return matchShift && matchStatus && matchSearch;
    });

    // Tính toán tổng hợp số liệu hóa đơn hiển thị tại quầy
    let totalAllOrders = 0;
    let validOrderTotal = 0;
    let paidTotal = 0;

    filtered.forEach((ord) => {
        const amt = Number(ord.total_amount || 0);
        totalAllOrders += amt;
        const isCancelled = String(ord.order_status).toUpperCase() === "CANCELLED_ORDER";
        if (!isCancelled) {
            validOrderTotal += amt;
            const paid = Number(
                ord.net_paid_amount ??
                ord.allocated_amount ??
                (String(ord.payment_status).toUpperCase() === "PAID" ? amt : 0)
            );
            paidTotal += paid;
        }
    });

    const remainingTotal = Math.max(0, validOrderTotal - paidTotal);

    // Cập nhật thanh tóm tắt đối soát tại quầy
    const elTotal = document.getElementById("pos-stat-total");
    const elCount = document.getElementById("pos-stat-count");
    const elValid = document.getElementById("pos-stat-valid");
    const elPaid = document.getElementById("pos-stat-paid");
    const elRem = document.getElementById("pos-stat-remaining");

    if (elTotal) elTotal.textContent = formatVND(totalAllOrders);
    if (elCount) elCount.textContent = `(${filtered.length} đơn)`;
    if (elValid) elValid.textContent = formatVND(validOrderTotal);
    if (elPaid) elPaid.textContent = formatVND(paidTotal);
    if (elRem) elRem.textContent = formatVND(remainingTotal);

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-secondary">
                    Chưa có hóa đơn nào phù hợp với bộ lọc.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered
        .map((ord) => {
            const total = Number(ord.total_amount || 0);
            const isCancelled = String(ord.order_status).toUpperCase() === "CANCELLED_ORDER";
            const paid = Number(
                ord.net_paid_amount ??
                ord.allocated_amount ??
                (String(ord.payment_status).toUpperCase() === "PAID" ? total : 0)
            );
            const remaining = isCancelled ? 0 : Math.max(0, total - paid);
            const qrObj = ord.qr_request || ord.active_payment_request || null;
            const qrStatus = qrObj ? qrObj.status : (ord.qr_status || "UNISSUED");
            const isPaid = String(ord.payment_status || "").toUpperCase() === "PAID";

            return `
                <tr class="${isCancelled ? "table-light text-muted" : ""}">
                    <td>
                        <div class="d-flex align-items-center gap-1">
                            <span class="fw-bold ${isCancelled ? "text-muted text-decoration-line-through" : "text-dark"}">${escapePosHtml(ord.order_code)}</span>
                            <span class="badge bg-light text-secondary border" style="font-size:0.65rem">Ca ${ord.shift_id}</span>
                        </div>
                        <div class="text-secondary" style="font-size: 0.74rem;">
                            ${escapePosHtml(ord.note || formatDateTime(ord.created_at))}
                        </div>
                    </td>
                    <td class="text-end fw-bold font-numeric">
                        ${
                            isCancelled
                                ? `<span class="text-decoration-line-through text-muted">${formatVND(total)}</span>
                                   <div class="text-danger small" style="font-size:0.68rem">Không tính sổ quỹ</div>`
                                : formatVND(total)
                        }
                    </td>
                    <td class="text-end font-numeric">
                        ${
                            isCancelled
                                ? `<div class="text-muted small">—</div>`
                                : `<div class="fw-semibold text-success">${formatVND(paid)}</div>
                                   ${
                                       remaining > 0
                                           ? `<div class="text-warning small" style="font-size: 0.74rem;">Còn thiếu: <strong>${formatVND(remaining)}</strong></div>`
                                           : `<div class="text-secondary small" style="font-size: 0.74rem;">Hoàn tất</div>`
                                   }`
                        }
                    </td>
                    <td>
                        <div class="d-flex flex-column align-items-start gap-1">
                            ${
                                isCancelled
                                    ? `<span class="fp-badge fp-badge-danger">Đã hủy (Không tính sổ quỹ)</span>`
                                    : renderStatusBadge(ord.payment_status || "UNPAID")
                            }
                        </div>
                    </td>
                    <td class="text-end">
                        ${
                            isCancelled
                                ? `<button type="button" class="btn btn-sm btn-light border text-muted py-1 px-2" disabled style="font-size: 0.75rem;">
                                       Đã hủy đơn
                                   </button>`
                                : isPaid
                                ? `<button type="button" class="btn-fp-outline py-1 px-3" style="font-size: 0.78rem;" onclick="openOrderQrModal(${ord.id}, false)">
                                       Xem biên lai
                                   </button>`
                                : `<button type="button" class="btn-fp-dark py-1 px-3" style="font-size: 0.78rem;" onclick="openOrderQrModal(${ord.id}, true)">
                                       ${getHeroicon("qr-code", "hi-icon hi-icon-sm")}
                                       <span>${qrStatus === "ACTIVE" ? "Hiện mã QR" : "Xuất mã QR"}</span>
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}"""

pos_js = pos_js.replace(old_render_pos_table, new_render_pos_table)

with open("frontend/js/pos.js", "w", encoding="utf-8") as f:
    f.write(pos_js)
print("Updated frontend/js/pos.js successfully.")
