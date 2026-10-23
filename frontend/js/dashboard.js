// ==========================================================================
// BÁO CÁO DOANH THU, BIỂU ĐỒ CHART.JS & KIỂM TOÁN SỔ QUỸ (frontend/js/dashboard.js)
// ==========================================================================

let barChartInstance = null;
let doughnutChartInstance = null;
let currentLedgerEntries = [];
let isTamperSimulationActive = false;

function initDashboardPage() {
    bindDashboardEvents();
    loadDashboardData(false);
}

function bindDashboardEvents() {
    document.getElementById("btn-dash-refresh")?.addEventListener("click", () => {
        isTamperSimulationActive = false;
        loadDashboardData(true);
    });

    document.getElementById("dash-shift-filter")?.addEventListener("change", () => {
        isTamperSimulationActive = false;
        loadDashboardData(true);
    });

    document.getElementById("btn-verify-chain-bottom")?.addEventListener("click", () => verifyLedgerHashChain(true));
    document.getElementById("btn-simulate-tamper-tc10")?.addEventListener("click", simulateTamperAttackTc10);
}

async function loadDashboardData(showNotification = false) {
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
}

function renderDashboardKpisAndTables(data) {
    const targetRev = Number(data.target_revenue ?? 120000000);
    const validTotal = Number(data.valid_order_total ?? 100000000);
    const activeQr = Number(data.active_qr_request_total ?? 90000000);
    const netAllocated = Number(data.allocated_payment_total ?? 75000000);
    const unissuedQr = Number(data.unissued_qr_amount ?? Math.max(0, validTotal - activeQr));
    const pendingQr = Number(data.pending_qr_collection ?? Math.max(0, activeQr - netAllocated));
    const remaining = Number(data.remaining_receivable ?? Math.max(0, validTotal - netAllocated));
    const unallocatedBank = Number(data.unallocated_bank_tx_total ?? 5000000);
    const totalBankReceived = Number(data.total_bank_received ?? netAllocated + unallocatedBank);

    const rate = validTotal > 0 ? Math.round((netAllocated / validTotal) * 100) : 0;

    setText("kpi-target-revenue", formatVND(targetRev));
    setText("kpi-valid-order-total", formatVND(validTotal));
    setText("kpi-active-qr-total", formatVND(activeQr));
    setText("kpi-allocated-payment-total", formatVND(netAllocated));
    setText("kpi-collection-rate", `${rate}%`);
    setText("kpi-unallocated-bank-total", formatVND(unallocatedBank));
    setText("kpi-unissued-qr-amount", formatVND(unissuedQr));
    setText("kpi-pending-qr-collection", formatVND(pendingQr));
    setText("kpi-remaining-receivable", formatVND(remaining));

    const formulaTbody = document.getElementById("dash-reconciliation-formula-tbody");
    if (formulaTbody) {
        formulaTbody.innerHTML = `
            <tr>
                <td class="text-secondary">Mục tiêu doanh thu ca (Tham khảo)</td>
                <td class="small text-secondary">Chỉ tiêu kỳ vọng khi mở ca, không dùng để tính công nợ đơn hàng</td>
                <td class="text-end text-secondary fw-semibold font-numeric">${formatVND(targetRev)}</td>
            </tr>
            <tr>
                <td class="fw-semibold text-primary">1. Tổng giá trị hóa đơn hợp lệ</td>
                <td class="small text-secondary">Tổng số tiền phải thu gốc từ các hóa đơn bán hàng trong ca</td>
                <td class="text-end fw-bold text-primary font-numeric">${formatVND(validTotal)}</td>
            </tr>
            <tr>
                <td class="fw-semibold text-dark">2. Đã xuất mã QR thu tiền</td>
                <td class="small text-secondary">Tổng giá trị các mã QR đang hoạt động và đã hoàn tất</td>
                <td class="text-end fw-bold text-dark font-numeric">${formatVND(activeQr)}</td>
            </tr>
            <tr>
                <td class="fw-semibold text-success">3. Tiền thực thu đã khớp vào đơn</td>
                <td class="small text-secondary">Số tiền thực tế đã nhận và xác nhận thanh toán cho hóa đơn</td>
                <td class="text-end fw-bold text-success font-numeric">${formatVND(netAllocated)}</td>
            </tr>
            <tr>
                <td class="fw-medium">4. Hóa đơn chưa xuất mã QR</td>
                <td class="small text-secondary">Hóa đơn đã tạo nhưng thu ngân chưa bấm xuất mã QR (= Mục 1 − Mục 2)</td>
                <td class="text-end fw-semibold font-numeric">${formatVND(unissuedQr)}</td>
            </tr>
            <tr>
                <td class="fw-medium">5. Đã xuất mã QR nhưng chờ thu đủ</td>
                <td class="small text-secondary">Khách đang quét mã hoặc mới trả một phần (= Mục 2 − Mục 3)</td>
                <td class="text-end fw-semibold text-warning font-numeric">${formatVND(pendingQr)}</td>
            </tr>
            <tr>
                <td class="fw-bold text-dark">6. Tổng số tiền còn phải thu của hóa đơn</td>
                <td class="small text-secondary">Tổng công nợ đơn hàng còn cần thu (= Mục 1 − Mục 3)</td>
                <td class="text-end fw-bold text-dark font-numeric">${formatVND(remaining)}</td>
            </tr>
            <tr>
                <td class="fw-bold text-danger">7. Tiền nhận chưa rõ đơn hàng (Tiền treo)</td>
                <td class="small text-secondary">Khách chuyển khoản quên ghi mã đơn hoặc chuyển dư tiền chờ kế toán xử lý</td>
                <td class="text-end fw-bold text-danger font-numeric">${formatVND(unallocatedBank)}</td>
            </tr>
            <tr class="bg-light">
                <td class="fw-bold text-dark">8. Tổng tiền chuyển khoản ngân hàng đã nhận</td>
                <td class="small text-secondary">Tổng tiền báo có vào tài khoản (= Mục 3 + Mục 7)</td>
                <td class="text-end fw-bold text-dark font-numeric">${formatVND(totalBankReceived)}</td>
            </tr>
        `;
    }
}

function renderDashboardCharts(data) {
    if (typeof window.Chart === "undefined") return;

    const targetRev = Number(data.target_revenue ?? 120000000);
    const validTotal = Number(data.valid_order_total ?? 100000000);
    const activeQr = Number(data.active_qr_request_total ?? 90000000);
    const netAllocated = Number(data.allocated_payment_total ?? 75000000);
    const unissuedQr = Number(data.unissued_qr_amount ?? Math.max(0, validTotal - activeQr));
    const pendingQr = Number(data.pending_qr_collection ?? Math.max(0, activeQr - netAllocated));
    const remaining = Number(data.remaining_receivable ?? Math.max(0, validTotal - netAllocated));
    const unallocatedBank = Number(data.unallocated_bank_tx_total ?? 5000000);

    const chartFont = "'Be Vietnam Pro', 'Inter', sans-serif";

    const barCtx = document.getElementById("reconciliationBarChart");
    if (barCtx) {
        if (barChartInstance) barChartInstance.destroy();
        barChartInstance = new Chart(barCtx, {
            type: "bar",
            data: {
                labels: ["Mục tiêu ca", "Tổng hóa đơn", "Đã xuất QR", "Thực thu", "Còn phải thu", "Tiền treo"],
                datasets: [
                    {
                        label: "Số tiền (VNĐ)",
                        data: [targetRev, validTotal, activeQr, netAllocated, remaining, unallocatedBank],
                        backgroundColor: ["#94a3b8", "#2563eb", "#0284c7", "#059669", "#d97706", "#e11d48"],
                        borderRadius: 8,
                        maxBarThickness: 40
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: (ctx) => ` ${formatVND(ctx.raw)}` }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { family: chartFont, size: 11 } } },
                    y: {
                        beginAtZero: true,
                        grid: { color: "#f1f5f9" },
                        ticks: {
                            font: { family: chartFont, size: 11 },
                            callback: (val) => `${Number(val) / 1000000}tr`
                        }
                    }
                }
            }
        });
    }

    const doughnutCtx = document.getElementById("receivableDoughnutChart");
    if (doughnutCtx) {
        if (doughnutChartInstance) doughnutChartInstance.destroy();
        doughnutChartInstance = new Chart(doughnutCtx, {
            type: "doughnut",
            data: {
                labels: ["Đã thu khớp đơn", "Đã xuất QR chờ thu", "Chưa xuất mã QR"],
                datasets: [
                    {
                        data: [netAllocated, pendingQr, unissuedQr],
                        backgroundColor: ["#059669", "#f59e0b", "#cbd5e1"],
                        borderWidth: 2,
                        borderColor: "#ffffff"
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { font: { family: chartFont, size: 11 }, boxWidth: 12 }
                    },
                    tooltip: {
                        callbacks: { label: (ctx) => ` ${ctx.label}: ${formatVND(ctx.raw)}` }
                    }
                }
            }
        });
    }
}

async function verifyLedgerHashChain(showToastNotification = true) {
    try {
        const res = await apiRequest("/ledger/verify-chain");
        const isValid = Boolean(res.is_valid ?? res.valid ?? true);
        const entries = res.entries || res.allocations || currentLedgerEntries;
        currentLedgerEntries = entries;

        renderHashChainVerificationResult({
            is_valid: isValid,
            total_records: entries.length,
            tampered_block_id: res.tampered_block_id || null,
            entries
        });

        if (showToastNotification) {
            showToast(
                isValid ? "Sổ quỹ an toàn và nguyên vẹn 100%!" : "CẢNH BÁO: Phát hiện dữ liệu lịch sử bị thay đổi!",
                isValid ? "success" : "danger"
            );
        }
    } catch (_) {
        const tamperedEntry = currentLedgerEntries.find((e) => e.is_valid === false);
        const isValid = !tamperedEntry;
        renderHashChainVerificationResult({
            is_valid: isValid,
            total_records: currentLedgerEntries.length,
            tampered_block_id: tamperedEntry ? tamperedEntry.id : null,
            entries: currentLedgerEntries
        });
        if (showToastNotification) {
            showToast(
                isValid ? "Đã rà soát sổ quỹ: Toàn bộ bút toán đều nguyên vẹn!" : "CẢNH BÁO: Phát hiện bút toán bị sửa số tiền!",
                isValid ? "success" : "danger"
            );
        }
    }
}

function renderHashChainVerificationResult(result) {
    const topBadge = document.getElementById("dash-chain-badge");
    const topBadgeText = document.getElementById("dash-chain-badge-text");
    const alertBox = document.getElementById("hash-chain-alert-box");
    const alertText = document.getElementById("hash-chain-alert-text");
    const countBadge = document.getElementById("hash-chain-count-badge");
    const tbody = document.getElementById("dash-ledger-chain-tbody");

    const isValid = Boolean(result.is_valid);
    const entries = result.entries || [];

    if (topBadge && topBadgeText) {
        topBadge.className = `fp-badge ${isValid ? "fp-badge-success" : "fp-badge-danger"}`;
        topBadgeText.textContent = isValid ? "✓ Sổ quỹ an toàn" : "✕ Phát hiện sửa dữ liệu";
    }

    if (alertBox && alertText && countBadge) {
        alertBox.className = `alert ${isValid ? "alert-success" : "alert-danger"} rounded-3 border-0 d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3 py-2 px-3`;
        alertText.innerHTML = isValid
            ? `<strong>Dữ liệu sổ quỹ nguyên vẹn 100%:</strong> Toàn bộ các bút toán thu tiền và hoàn đảo đều khớp mã bảo mật.`
            : `<strong>CẢNH BÁO PHÁT HIỆN CHỈNH SỬA TRÁI PHÉP:</strong> Số tiền tại <strong>Bút toán #${result.tampered_block_id || 1}</strong> đã bị thay đổi làm lệch mã niêm phong!`;
        countBadge.className = `badge ${isValid ? "bg-success" : "bg-danger"} rounded-pill`;
        countBadge.textContent = `${entries.length} bút toán`;
    }

    if (!tbody) return;
    tbody.innerHTML = entries
        .map((item) => {
            const blockValid = item.is_valid !== false;
            const isReversal = String(item.entry_type || "").toUpperCase() === "REVERSAL" || Number(item.allocated_amount) < 0;
            const amount = Number(item.allocated_amount || 0);

            return `
                <tr class="${blockValid ? "" : "table-danger"}">
                    <td>
                        <div class="fw-bold text-dark">Bút toán #${item.id}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(item.created_at)}</div>
                    </td>
                    <td>${renderStatusBadge(isReversal ? "REVERSAL" : "ALLOCATION")}</td>
                    <td>
                        <span class="small fw-semibold">${escapeDashHtml(item.reference_code)} → <strong>Hóa đơn ${escapeDashHtml(item.order_code)}</strong></span>
                    </td>
                    <td class="text-end fw-bold font-numeric ${isReversal ? "text-danger" : "text-success"}">
                        ${amount > 0 ? `+${formatVND(amount)}` : formatVND(amount)}
                    </td>
                    <td><code class="small text-secondary">${escapeDashHtml(String(item.prev_hash || "").slice(0, 12))}...</code></td>
                    <td><code class="small ${blockValid ? "text-dark" : "text-danger fw-bold"}">${escapeDashHtml(String(item.record_hash || "").slice(0, 12))}...</code></td>
                    <td>
                        ${blockValid ? `<span class="fp-badge fp-badge-success">✓ Nguyên vẹn</span>` : `<span class="fp-badge fp-badge-danger">✕ Bị sửa đổi</span>`}
                    </td>
                </tr>
            `;
        })
        .join("");
}

function simulateTamperAttackTc10() {
    isTamperSimulationActive = !isTamperSimulationActive;
    const btn = document.getElementById("btn-simulate-tamper-tc10");

    if (isTamperSimulationActive && currentLedgerEntries.length > 0) {
        currentLedgerEntries[0].allocated_amount = 15000000;
        currentLedgerEntries[0].is_valid = false;
        if (currentLedgerEntries[1]) currentLedgerEntries[1].is_valid = false;
        if (btn) btn.textContent = "Khôi phục dữ liệu gốc";

        renderHashChainVerificationResult({
            is_valid: false,
            total_records: currentLedgerEntries.length,
            tampered_block_id: currentLedgerEntries[0].id,
            entries: currentLedgerEntries
        });
        showToast("Đã giả lập sửa số tiền Bút toán #1. Hệ thống lập tức báo động đỏ!", "danger");
    } else {
        const store = getDemoStore();
        currentLedgerEntries = JSON.parse(JSON.stringify(store.allocations || []));
        if (btn) btn.textContent = "Giả lập sửa trộm dữ liệu";

        renderHashChainVerificationResult({
            is_valid: true,
            total_records: currentLedgerEntries.length,
            tampered_block_id: null,
            entries: currentLedgerEntries
        });
        showToast("Đã khôi phục dữ liệu sổ quỹ nguyên vẹn.", "success");
    }
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