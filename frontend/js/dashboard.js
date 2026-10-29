// ==========================================================================
// BÁO CÁO DOANH THU, BIỂU ĐỒ CHART.JS & KIỂM TOÁN SỔ QUỸ (frontend/js/dashboard.js)
// ==========================================================================

let barChartInstance = null;
let doughnutChartInstance = null;
let currentLedgerEntries = [];
let originalLedgerEntriesBackup = [];
let isTamperSimulationActive = false;
let hasAppliedInitialUrlShift = false;
let currentSelectedDate = "";
let currentSelectedShiftId = "ALL";

function initDashboardPage() {
    bindDashboardEvents();
    loadDashboardData(false);
}

function bindDashboardEvents() {
    // 1. Khi chọn ngày (Tầng 1) -> Tự động reset ca về "Tất cả các ca trong ngày"
    document.getElementById("dash-date-filter")?.addEventListener("change", (e) => {
        currentSelectedDate = e.target.value;
        currentSelectedShiftId = "ALL";
        const shiftFilter = document.getElementById("dash-shift-filter");
        if (shiftFilter) shiftFilter.value = "ALL";
        isTamperSimulationActive = false;
        loadDashboardData(false);
    });

    // 2. Khi chọn ca làm việc trong ngày (Tầng 2)
    document.getElementById("dash-shift-filter")?.addEventListener("change", (e) => {
        currentSelectedShiftId = e.target.value;
        isTamperSimulationActive = false;
        loadDashboardData(false);
    });

    // 3. Nút làm mới dữ liệu
    document.getElementById("btn-dash-refresh")?.addEventListener("click", () => {
        isTamperSimulationActive = false;
        const btn = document.getElementById("btn-simulate-tamper-tc10");
        if (btn) btn.textContent = "Giả lập sửa trộm dữ liệu";
        loadDashboardData(true);
    });

    document.getElementById("btn-verify-chain-bottom")?.addEventListener("click", () => verifyLedgerHashChain(true));
    document.getElementById("btn-simulate-tamper-tc10")?.addEventListener("click", simulateTamperAttackTc10);
}

function updateDashboardShiftDropdown(dayShifts, currentShiftId) {
    const filterEl = document.getElementById("dash-shift-filter");
    if (!filterEl) return;

    if (!Array.isArray(dayShifts) || dayShifts.length === 0) {
        filterEl.innerHTML = '<option value="ALL">Chưa có ca trong ngày này</option>';
        filterEl.disabled = false;
        filterEl.value = "ALL";
        return;
    }

    filterEl.disabled = false;
    let html = '<option value="ALL">Tất cả các ca trong ngày</option>';
    dayShifts.forEach((s) => {
        const statusLabel = String(s.status).toUpperCase() === "OPEN" ? "(Đang mở)" : "(Đã đóng)";
        html += `<option value="${s.id}">Ca ${s.id}: ${escapeDashHtml(s.name)} ${statusLabel}</option>`;
    });
    filterEl.innerHTML = html;

    const targetVal = String(currentShiftId || "ALL");
    if (Array.from(filterEl.options).some(o => o.value === targetVal)) {
        filterEl.value = targetVal;
    } else {
        filterEl.value = "ALL";
    }
}

async function loadDashboardData(showNotification = false) {
    let summaryData = null;
    const urlParams = new URLSearchParams(window.location.search);
    const preferredShiftId = urlParams.get("shift_id");
    const preferredDate = urlParams.get("date");
    const dateInput = document.getElementById("dash-date-filter");
    const filterEl = document.getElementById("dash-shift-filter");

    if (!hasAppliedInitialUrlShift) {
        if (preferredDate) {
            currentSelectedDate = preferredDate;
            if (dateInput) dateInput.value = preferredDate;
        }
        if (preferredShiftId) {
            currentSelectedShiftId = preferredShiftId;
        }
        hasAppliedInitialUrlShift = true;
    }

    const queryParts = [];
    if (currentSelectedDate) {
        queryParts.push(`date=${encodeURIComponent(currentSelectedDate)}`);
    }
    if (currentSelectedShiftId) {
        queryParts.push(`shift_id=${encodeURIComponent(currentSelectedShiftId)}`);
    }
    const query = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";

    try {
        summaryData = await apiRequest(`/dashboard/summary${query}`);
    } catch (_) {
        const store = getDemoStore();
        summaryData = computeStoreSummary(store, currentSelectedShiftId || "ALL");
    }

    // Đồng bộ ngày vào Date Picker
    if (summaryData.selected_date) {
        currentSelectedDate = summaryData.selected_date;
        if (dateInput && dateInput.value !== summaryData.selected_date) {
            dateInput.value = summaryData.selected_date;
        }
    }

    // Cập nhật danh sách ca trong ngày vào Dropdown Ca
    const shiftsForDropdown = summaryData.day_shifts || summaryData.available_shifts || [];
    const targetSelectVal = String(summaryData.shift_id ?? currentSelectedShiftId ?? "ALL");
    updateDashboardShiftDropdown(shiftsForDropdown, targetSelectVal);
    currentSelectedShiftId = targetSelectVal;

    currentLedgerEntries = JSON.parse(JSON.stringify(summaryData.ledger_entries || []));
    originalLedgerEntriesBackup = JSON.parse(JSON.stringify(currentLedgerEntries));

    const isChainValid = Boolean(summaryData.ledger_integrity_valid ?? true);
    isTamperSimulationActive = !isChainValid;
    const tamperBtn = document.getElementById("btn-simulate-tamper-tc10");
    if (tamperBtn) {
        tamperBtn.textContent = isTamperSimulationActive ? "Khôi phục dữ liệu gốc" : "Giả lập sửa trộm dữ liệu";
    }

    const corruptedEntry = currentLedgerEntries.find((e) => e.is_valid === false);

    renderDashboardKpisAndTables(summaryData);
    renderDashboardOrdersTable(summaryData.orders || []);
    renderDashboardCharts(summaryData);
    renderHashChainVerificationResult({
        is_valid: isChainValid,
        total_records: currentLedgerEntries.length,
        tampered_block_id: corruptedEntry ? corruptedEntry.id : null,
        entries: currentLedgerEntries
    });

    if (showNotification) {
        showToast("Đã cập nhật số liệu báo cáo mới nhất.", "success");
    }
}

function renderDashboardKpisAndTables(data) {
    const targetRev = Number(data.target_revenue ?? 0);
    const validTotal = Number(data.valid_order_total ?? 0);
    const activeQr = Number(data.active_qr_request_total ?? 0);
    const netAllocated = Number(data.allocated_payment_total ?? 0);
    const unissuedQr = Number(data.unissued_qr_amount ?? Math.max(0, validTotal - activeQr));
    const pendingQr = Number(data.pending_qr_collection ?? Math.max(0, activeQr - netAllocated));
    const remaining = Number(data.remaining_receivable ?? Math.max(0, validTotal - netAllocated));
    const unallocatedBank = Number(data.unallocated_bank_tx_total ?? 0);
    const totalBankReceived = Number(data.total_bank_received ?? netAllocated + unallocatedBank);

    const rate = validTotal > 0 ? Math.round((netAllocated / validTotal) * 100) : 0;

    // 1. Cập nhật các thẻ KPI trên cùng
    setText("kpi-target-revenue", formatVND(targetRev));
    setText("kpi-valid-order-total", formatVND(validTotal));
    setText("kpi-bank-received-total", formatVND(totalBankReceived));
    setText("kpi-allocated-payment-total", formatVND(netAllocated));
    setText("kpi-remaining-receivable", formatVND(remaining));
    setText("kpi-unallocated-bank-total", formatVND(unallocatedBank));

    // Khả năng tương thích cho các ID ẩn
    setText("kpi-active-qr-total", formatVND(activeQr));
    setText("kpi-unissued-qr-amount", formatVND(unissuedQr));
    setText("kpi-pending-qr-collection", formatVND(pendingQr));
    setText("kpi-collection-rate", `${rate}%`);

    // Số lượng đơn & giao dịch tương ứng
    const validCount = Number(data.valid_order_count ?? (data.orders ? data.orders.filter(o => o.order_status !== "CANCELLED_ORDER").length : 0));
    setText("dash-valid-order-count", `${validCount}`);

    const cancelledCount = Number(data.cancelled_order_count ?? (data.orders ? data.orders.filter(o => o.order_status === "CANCELLED_ORDER").length : 0));
    const cancelledTotal = Number(data.cancelled_order_total ?? 0);
    const cancelledRow = document.getElementById("dash-cancelled-order-row");
    if (cancelledRow) {
        if (cancelledCount > 0 || cancelledTotal > 0) {
            cancelledRow.classList.remove("d-none");
            setText("dash-cancelled-order-total", `${cancelledCount}`);
        } else {
            cancelledRow.classList.add("d-none");
        }
    }

    // Các nhãn phụ bên dưới số tiền
    const bankTxCount = Number(data.bank_transaction_count ?? (data.bank_transactions ? data.bank_transactions.length : (data.ledger_entries ? data.ledger_entries.length : 0)));
    setText("dash-bank-tx-count-label", `${bankTxCount} giao dịch thành công`);

    const allocatedCount = Number(data.allocated_order_count ?? (data.orders ? data.orders.filter(o => Number(o.net_paid_amount || 0) > 0).length : 0));
    setText("dash-allocated-count-label", `Khớp với ${allocatedCount} hóa đơn`);

    const unpaidCount = Number(data.unpaid_order_count ?? (data.orders ? data.orders.filter(o => o.order_status !== "CANCELLED_ORDER" && Math.max(0, Number(o.total_amount || 0) - Number(o.net_paid_amount || 0)) > 0).length : 0));
    setText("dash-unpaid-count-label", `${unpaidCount} hóa đơn chưa đủ`);

    const pendingTxCount = Number(data.unallocated_bank_tx_count ?? (data.bank_transactions ? data.bank_transactions.filter(t => Number(t.unallocated_amount || 0) > 0).length : 0));
    setText("dash-pending-tx-count-label", `${pendingTxCount} giao dịch cần xử lý`);

    // Chênh lệch hiện tại
    const diff = Math.max(0, remaining) + Math.max(0, unallocatedBank);
    setText("dash-diff-amount", formatVND(diff));

    // 2. Tab 2: Bảng Cân Đối Dòng Tiền (Khớp ảnh tham khảo 4)
    const formulaTbody = document.getElementById("dash-reconciliation-formula-tbody");
    if (formulaTbody) {
        formulaTbody.innerHTML = `
            <tr>
                <td class="fw-semibold text-dark">Tổng hóa đơn hợp lệ</td>
                <td class="text-secondary small">Giá trị hàng hóa cần thu, không gồm đơn đã hủy</td>
                <td class="text-end fw-bold font-numeric text-dark">${formatVND(validTotal)}</td>
            </tr>
            <tr>
                <td class="fw-semibold text-dark">Đã phân bổ</td>
                <td class="text-secondary small">Tiền ngân hàng đã khớp chính xác vào hóa đơn</td>
                <td class="text-end fw-bold font-numeric text-success">${formatVND(netAllocated)}</td>
            </tr>
            <tr>
                <td class="fw-semibold text-dark">Còn phải thu</td>
                <td class="text-secondary small">Phần khách hàng chưa thanh toán đủ</td>
                <td class="text-end fw-bold font-numeric" style="color: #d97706;">${formatVND(remaining)}</td>
            </tr>
            <tr>
                <td class="fw-semibold text-dark">Chờ xử lý</td>
                <td class="text-secondary small">Tiền đã về nhưng chưa xác định được hóa đơn</td>
                <td class="text-end fw-bold font-numeric text-danger">${formatVND(unallocatedBank)}</td>
            </tr>
        `;
    }
}

function renderDashboardCharts(data) {
    if (typeof window.Chart === "undefined") return;

    const chartFont = "'Be Vietnam Pro', 'Inter', sans-serif";
    const barCtx = document.getElementById("reconciliationBarChart");
    if (!barCtx) return;

    const isDaySummary = Boolean(data.is_day_summary);
    const chartTitle = document.getElementById("dash-chart-title");
    const chartSubtitle = document.getElementById("dash-chart-subtitle");
    const diffLabel = document.getElementById("dash-diff-label");
    const diffSubtext = document.getElementById("dash-diff-subtext");
    const legendItem3 = document.getElementById("legend-item-3");
    const legendText1 = document.getElementById("legend-text-1");
    const legendText2 = document.getElementById("legend-text-2");

    if (barChartInstance) {
        barChartInstance.destroy();
        barChartInstance = null;
    }

    if (isDaySummary) {
        // =====================================================================
        // CHẾ ĐỘ 1: BIẾN ĐỘNG DOANH THU THEO TỪNG CA TRONG NGÀY
        // =====================================================================
        if (chartTitle) chartTitle.textContent = "Biến động doanh thu theo từng ca";
        if (chartSubtitle) chartSubtitle.textContent = `So sánh tổng hóa đơn và tiền thực nhận giữa các ca trong ngày (${data.selected_date || ""})`;
        if (diffLabel) diffLabel.textContent = "Chênh lệch ngày";
        if (diffSubtext) diffSubtext.textContent = "Tổng chênh lệch giữa hóa đơn và thực thu các ca trong ngày";
        if (legendText1) legendText1.textContent = "Hóa đơn";
        if (legendText2) legendText2.textContent = "Thực thu";
        if (legendItem3) legendItem3.classList.remove("d-none");

        const shiftList = data.shift_breakdown || [];

        let labels = [];
        let invoiceData = [];
        let receivedData = [];
        let targetData = [];

        if (shiftList.length === 0) {
            labels = ["Chưa có ca trong ngày"];
            invoiceData = [0];
            receivedData = [0];
            targetData = [0];
        } else {
            labels = shiftList.map((s) => {
                const name = s.shift_name || `Ca ${s.shift_id}`;
                return name.length > 20 ? name.slice(0, 18) + "..." : name;
            });
            invoiceData = shiftList.map((s) => Number(s.valid_order_total || 0));
            receivedData = shiftList.map((s) => Number(s.allocated_payment_total || 0));
            targetData = shiftList.map((s) => Number(s.target_revenue || 0));
        }

        barChartInstance = new Chart(barCtx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        type: "bar",
                        label: "Hóa đơn",
                        data: invoiceData,
                        backgroundColor: "#1e3a8a",
                        borderRadius: 6,
                        barPercentage: 0.55,
                        categoryPercentage: 0.5
                    },
                    {
                        type: "bar",
                        label: "Thực thu",
                        data: receivedData,
                        backgroundColor: "#10b981",
                        borderRadius: 6,
                        barPercentage: 0.55,
                        categoryPercentage: 0.5
                    },
                    {
                        type: "line",
                        label: "Mục tiêu ca",
                        data: targetData,
                        borderColor: "#f59e0b",
                        backgroundColor: "#f59e0b",
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.dataset.label}: ${formatVND(ctx.raw)}`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { family: chartFont, size: 11, weight: "500" }, color: "#64748b" }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "#f1f5f9" },
                        ticks: {
                            font: { family: chartFont, size: 11 },
                            color: "#94a3b8",
                            callback: (val) => `${Number(val) / 1000000} tr`
                        }
                    }
                }
            }
        });

        // Chênh lệch toàn ngày
        const validTotal = Number(data.valid_order_total ?? 0);
        const netAllocated = Number(data.allocated_payment_total ?? 0);
        const unallocatedBank = Number(data.unallocated_bank_tx_total ?? 0);
        const diffDay = Math.max(0, validTotal - netAllocated) + unallocatedBank;
        setText("dash-diff-amount", formatVND(diffDay));

    } else {
        // =====================================================================
        // CHẾ ĐỘ 2: BIỂU ĐỒ CHÊNH LỆCH DÒNG TIỀN TRONG 1 CA CỤ THỂ
        // =====================================================================
        if (chartTitle) chartTitle.textContent = `Dòng tiền & Chênh lệch ca: ${data.shift_name || ("Ca " + data.shift_id)}`;
        if (chartSubtitle) chartSubtitle.textContent = "Phân tích đối soát các thành phần tài chính và chênh lệch trong ca";
        if (diffLabel) diffLabel.textContent = "Chênh lệch ca";
        if (diffSubtext) diffSubtext.textContent = "Bao gồm tiền còn phải thu và giao dịch chờ xử lý của ca";
        if (legendText1) legendText1.textContent = "Đã khớp / Thu đủ";
        if (legendText2) legendText2.textContent = "Chờ thu / Treo";
        if (legendItem3) legendItem3.classList.add("d-none");

        const validTotal = Number(data.valid_order_total ?? 0);
        const netAllocated = Number(data.allocated_payment_total ?? 0);
        const pendingQr = Number(data.pending_qr_collection ?? 0);
        const unallocatedBank = Number(data.unallocated_bank_tx_total ?? 0);
        const remaining = Number(data.remaining_receivable ?? Math.max(0, validTotal - netAllocated));

        const labels = ["Hóa đơn hợp lệ", "Đã thu ngân hàng", "Chờ quét QR", "Tiền thừa / Chờ xử lý"];
        const values = [validTotal, netAllocated, pendingQr, unallocatedBank];
        const colors = ["#1e3a8a", "#10b981", "#3b82f6", "#f59e0b"];

        barChartInstance = new Chart(barCtx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Số tiền",
                        data: values,
                        backgroundColor: colors,
                        borderRadius: 6,
                        barPercentage: 0.5,
                        categoryPercentage: 0.6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.label}: ${formatVND(ctx.raw)}`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { family: chartFont, size: 11, weight: "500" }, color: "#64748b" }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "#f1f5f9" },
                        ticks: {
                            font: { family: chartFont, size: 11 },
                            color: "#94a3b8",
                            callback: (val) => `${Number(val) / 1000000} tr`
                        }
                    }
                }
            }
        });

        // Chênh lệch trong ca
        const diffShift = Math.max(0, remaining) + unallocatedBank;
        setText("dash-diff-amount", formatVND(diffShift));
    }
}

function renderHashChainVerificationResult(result) {
    const topBadge = document.getElementById("dash-chain-badge");
    const topBadgeText = document.getElementById("dash-chain-badge-text");
    const tbody = document.getElementById("dash-ledger-chain-tbody");

    const isValid = Boolean(result.is_valid);
    const entries = result.entries || [];

    if (topBadge && topBadgeText) {
        topBadge.className = `d-flex align-items-center gap-1 ${isValid ? "badge-recon-green" : "badge-recon-danger"}`;
        topBadgeText.textContent = isValid ? "✓ Sổ quỹ cân bằng" : "✕ Phát hiện sửa dữ liệu";
    }

    if (!tbody) return;
    if (entries.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-secondary">
                    Chưa có bút toán nào trong sổ cái đối soát của ca.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = entries
        .map((item) => {
            const blockValid = item.is_valid !== false;
            const isReversal = String(item.entry_type || "").toUpperCase() === "REVERSAL" || Number(item.allocated_amount) < 0;
            const amount = Number(item.allocated_amount || 0);

            // Tách giờ phút
            const dt = new Date(String(item.created_at || "").replace(" ", "T"));
            const timeStr = !isNaN(dt.getTime())
                ? dt.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false })
                : "—";

            // Nội dung theo chuẩn Ảnh 3
            let contentDesc = "";
            if (isReversal) {
                contentDesc = "Hủy hóa đơn";
            } else if (item.is_partial || (amount > 0 && amount < 1000000 && item.order_total && amount < item.order_total)) {
                contentDesc = "Thu một phần";
            } else {
                contentDesc = "Thu tiền hóa đơn";
            }

            // Tham chiếu (HD-xxxx)
            const refStr = item.order_code
                ? (item.order_code.startsWith("HD") ? item.order_code : `HD-${item.order_code.replace(/^(ORD|HD)-?/i, "")}`)
                : (item.reference_code || `Bút toán #${item.id}`);

            // Ghi tăng / Ghi giảm
            const increaseStr = amount > 0 ? `+${formatVND(amount)}` : "—";
            const decreaseStr = amount < 0 ? `-${formatVND(Math.abs(amount))}` : isReversal ? `-${formatVND(Math.abs(amount || 0))}` : "—";

            // Huy hiệu kiểm tra
            let checkBadge = "";
            if (!blockValid) {
                checkBadge = `<span class="badge-recon-danger">Bị sửa đổi</span>`;
            } else if (isReversal) {
                checkBadge = `<span class="badge-recon-danger">Loại trừ</span>`;
            } else {
                checkBadge = `<span class="badge-recon-green">Hợp lệ</span>`;
            }

            return `
                <tr class="${blockValid ? "" : "table-danger"}">
                    <td class="font-numeric text-secondary">${timeStr}</td>
                    <td class="fw-medium text-dark">${escapeDashHtml(contentDesc)}</td>
                    <td class="fw-bold font-numeric text-dark">${escapeDashHtml(refStr)}</td>
                    <td class="fw-bold font-numeric text-success">${increaseStr}</td>
                    <td class="fw-bold font-numeric text-danger">${decreaseStr}</td>
                    <td>${checkBadge}</td>
                </tr>
            `;
        })
        .join("");
}

function renderDashboardOrdersTable(orders) {
    const tbody = document.getElementById("dash-orders-table-tbody");
    const countBadge = document.getElementById("dash-orders-count-badge");
    if (!tbody) return;

    if (!orders || orders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5 text-secondary">
                    Chưa có hóa đơn nào trong phạm vi ca được chọn.
                </td>
            </tr>
        `;
        if (countBadge) countBadge.textContent = "0 hóa đơn";
        return;
    }

    if (countBadge) countBadge.textContent = `${orders.length} hóa đơn`;

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
            const isPaid = String(ord.payment_status).toUpperCase() === "PAID" || (remaining === 0 && !isCancelled && paid > 0);
            const isPartial = String(ord.payment_status).toUpperCase() === "PARTIALLY_PAID" || (paid > 0 && remaining > 0 && !isCancelled);

            const ordCodeStr = ord.order_code
                ? (ord.order_code.startsWith("HD") ? ord.order_code : `HD-${ord.order_code.replace(/^(ORD|HD)-?/i, "")}`)
                : `HD #${ord.id}`;

            const dt = new Date(String(ord.created_at || "").replace(" ", "T"));
            const timeStr = !isNaN(dt.getTime())
                ? dt.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false })
                : "—";

            let statusBadge = "";
            if (isCancelled) {
                statusBadge = `<span class="badge-recon-danger">Đã hủy</span>`;
            } else if (isPaid) {
                statusBadge = `<span class="badge-recon-green">Đã thu đủ</span>`;
            } else if (isPartial) {
                statusBadge = `<span class="badge-recon-warning">Thu một phần</span>`;
            } else {
                statusBadge = `<span class="badge-recon-warning">Chờ thanh toán</span>`;
            }

            const refCode = ord.reference_code
                ? ord.reference_code.replace(/^(FT[0-9]{2})[0-9]+([0-9]{2})$/, "$1..$2")
                : (ord.bank_transaction_id ? `FT..${String(ord.bank_transaction_id).slice(-2)}` : "—");

            const auditBadge = isCancelled
                ? `<span class="badge-recon-danger">Loại trừ khỏi sổ quỹ</span>`
                : `<span class="badge-recon-green">Hạch toán sổ quỹ</span>`;

            return `
                <tr class="${isCancelled ? "text-muted" : ""}">
                    <td>
                        <strong class="font-numeric ${isCancelled ? "text-muted text-decoration-line-through" : "text-dark"}">${escapeDashHtml(ordCodeStr)}</strong>
                    </td>
                    <td class="font-numeric text-secondary">${timeStr}</td>
                    <td class="text-end fw-bold font-numeric ${isCancelled ? "text-decoration-line-through text-muted" : "text-dark"}">
                        ${formatVND(total)}
                    </td>
                    <td class="text-end font-numeric fw-semibold text-dark">
                        ${formatVND(paid)}
                    </td>
                    <td class="text-end font-numeric fw-semibold ${remaining > 0 && !isCancelled ? "text-dark" : "text-secondary"}">
                        ${isCancelled ? "—" : formatVND(remaining)}
                    </td>
                    <td>
                        ${statusBadge}
                    </td>
                    <td class="font-numeric text-secondary">
                        ${escapeDashHtml(refCode)}
                    </td>
                    <td>
                        ${auditBadge}
                    </td>
                </tr>
            `;
        })
        .join("");
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function escapeDashHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// Kiểm tra tính toàn vẹn chuỗi băm Sổ cái
async function verifyLedgerHashChain(showNotification = true) {
    try {
        const res = await apiRequest("/dashboard/verify-chain");
        renderHashChainVerificationResult({
            is_valid: res.is_valid,
            total_records: res.total_records ?? currentLedgerEntries.length,
            tampered_block_id: res.corrupted_record_id ?? res.tampered_block_id ?? null,
            entries: res.entries || currentLedgerEntries
        });
        if (showNotification) {
            if (res.is_valid) {
                showToast("Sổ cái toàn vẹn tuyệt đối! Không có dấu hiệu chỉnh sửa.", "success");
            } else {
                showToast(res.message || "Cảnh báo: Phát hiện chuỗi băm sổ cái bị đứt gãy!", "danger");
            }
        }
    } catch (_) {
        renderHashChainVerificationResult({
            is_valid: !isTamperSimulationActive,
            total_records: currentLedgerEntries.length,
            tampered_block_id: isTamperSimulationActive && currentLedgerEntries[0] ? currentLedgerEntries[0].id : null,
            entries: currentLedgerEntries
        });
        if (showNotification) {
            showToast(
                isTamperSimulationActive
                    ? "Cảnh báo: Phát hiện dữ liệu sổ cái bị thay đổi trái phép!"
                    : "Đã rà soát sổ quỹ: Chuỗi băm hợp lệ.",
                isTamperSimulationActive ? "danger" : "success"
            );
        }
    }
}

// Giả lập tấn công sửa trộm dữ liệu Sổ cái (Test Case TC-10)
function simulateTamperAttackTc10() {
    if (!currentLedgerEntries || currentLedgerEntries.length === 0) {
        showToast("Chưa có bút toán nào trong sổ cái để giả lập sửa dữ liệu.", "warning");
        return;
    }

    const btn = document.getElementById("btn-simulate-tamper-tc10");
    isTamperSimulationActive = !isTamperSimulationActive;

    if (isTamperSimulationActive) {
        currentLedgerEntries = JSON.parse(JSON.stringify(originalLedgerEntriesBackup));
        currentLedgerEntries[0].allocated_amount = Number(currentLedgerEntries[0].allocated_amount || 0) + 1000000;
        currentLedgerEntries[0].is_valid = false;
        if (btn) btn.textContent = "Khôi phục dữ liệu gốc";
        showToast("Đã giả lập sửa trộm +1.000.000 ₫ tại bút toán đầu tiên!", "danger");
    } else {
        currentLedgerEntries = JSON.parse(JSON.stringify(originalLedgerEntriesBackup));
        if (btn) btn.textContent = "Giả lập sửa trộm dữ liệu";
        showToast("Đã khôi phục dữ liệu sổ cái nguyên vẹn.", "info");
    }

    renderHashChainVerificationResult({
        is_valid: !isTamperSimulationActive,
        total_records: currentLedgerEntries.length,
        tampered_block_id: isTamperSimulationActive ? currentLedgerEntries[0].id : null,
        entries: currentLedgerEntries
    });
}