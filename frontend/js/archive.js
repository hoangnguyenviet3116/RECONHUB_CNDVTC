// ==========================================================================
// KHO LƯU TRỮ CA BÁN HÀNG — VIETQR RECONHUB (frontend/js/archive.js)
// Quản lý các ca đã đóng, niêm phong Merkle Root và hoàn tất kiểm toán
// ==========================================================================

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

let currentArchivedShifts = [];
let archivedSummaryMap = {};
let archivedMerkleMap = {};
let isFiltering = false;

function initArchivePage() {
    bindArchiveEvents();
    loadArchivedShifts(false);
}

function bindArchiveEvents() {
    // 1. Nút làm mới
    document.getElementById("btn-refresh-archive")?.addEventListener("click", () => {
        loadArchivedShifts(true);
    });

    // 2. Bộ chọn nhanh (Preset)
    document.getElementById("archive-preset-select")?.addEventListener("change", (e) => {
        applyPresetDateRange(e.target.value);
        loadArchivedShifts(false);
    });

    // 3. Thay đổi ngày
    document.getElementById("archive-from-date")?.addEventListener("change", () => {
        loadArchivedShifts(false);
    });
    document.getElementById("archive-to-date")?.addEventListener("change", () => {
        loadArchivedShifts(false);
    });

    // 4. Tìm kiếm ca
    document.getElementById("archive-search-shift")?.addEventListener("input", () => {
        filterAndRenderShifts();
    });
}

function applyPresetDateRange(preset) {
    const fromInput = document.getElementById("archive-from-date");
    const toInput = document.getElementById("archive-to-date");
    if (!fromInput || !toInput) return;

    const pad = (n) => String(n).padStart(2, "0");
    const toDateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    const now = new Date();

    if (preset === "ALL") {
        fromInput.value = "";
        toInput.value = "";
    } else if (preset === "TODAY") {
        fromInput.value = toDateStr(now);
        toInput.value = toDateStr(now);
    } else if (preset === "THIS_WEEK") {
        const d1 = new Date(now);
        const day = d1.getDay() || 7;
        d1.setDate(d1.getDate() - day + 1);
        const d2 = new Date(d1);
        d2.setDate(d2.getDate() + 6);
        fromInput.value = toDateStr(d1);
        toInput.value = toDateStr(d2);
    } else if (preset === "THIS_MONTH") {
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        fromInput.value = toDateStr(firstDay);
        toInput.value = toDateStr(lastDay);
    } else if (preset === "LAST_MONTH") {
        const firstDay = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
        fromInput.value = toDateStr(firstDay);
        toInput.value = toDateStr(lastDay);
    }
}

async function loadArchivedShifts(showNotification = false) {
    const container = document.getElementById("archived-shifts-container");
    const countLabel = document.getElementById("archived-list-status-label");
    const fromVal = document.getElementById("archive-from-date")?.value || "";
    const toVal = document.getElementById("archive-to-date")?.value || "";

    if (container) {
        container.innerHTML = `
            <div class="text-center py-5 text-secondary bg-white rounded-4 border">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                Đang nạp danh sách ca lưu trữ từ máy chủ...
            </div>
        `;
    }
    if (countLabel) countLabel.textContent = "Đang tải...";

    const params = new URLSearchParams();
    params.append("archived", "true");
    if (fromVal) params.append("from_date", fromVal);
    if (toVal) params.append("to_date", toVal);

    try {
        const data = await apiRequest(`/shifts?${params.toString()}`);
        currentArchivedShifts = Array.isArray(data) ? data : (data.items || data.shifts || []);
    } catch (err) {
        console.error("Lỗi tải danh sách ca lưu trữ:", err);
        currentArchivedShifts = [];
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger p-4 text-center rounded-4 border">
                    <strong>Không thể tải danh sách ca lưu trữ:</strong> ${escapeHtml(err.message || "Lỗi máy chủ")}
                </div>
            `;
        }
        if (countLabel) countLabel.textContent = "Lỗi kết nối";
        return;
    }

    // Tải thống kê doanh thu và kiểm toán Merkle cho các ca lưu trữ
    try {
        await fetchArchivedStatsAndAudits();
    } catch (err) {
        console.warn("Lỗi tải thống kê kiểm toán ca:", err);
    }

    filterAndRenderShifts();

    if (showNotification) {
        showToast("Đã cập nhật danh sách kho lưu trữ ca mới nhất.", "success");
    }
}

async function fetchArchivedStatsAndAudits() {
    archivedSummaryMap = {};
    archivedMerkleMap = {};

    try {
        const summaryData = await apiRequest("/dashboard/summary?shift_id=ALL");
        if (summaryData && Array.isArray(summaryData.orders)) {
            const orders = summaryData.orders;
            currentArchivedShifts.forEach((s) => {
                const sOrders = orders.filter((o) => Number(o.shift_id) === Number(s.id));
                const validOrders = sOrders.filter(
                    (o) => !["CANCELLED_ORDER"].includes(String(o.order_status || o.status || "").toUpperCase())
                );
                const rev = validOrders.reduce((sum, o) => {
                    const isPaid = String(o.payment_status).toUpperCase() === "PAID";
                    const paidAmount = Number(o.paid_amount || o.allocated_amount || 0);
                    return sum + (isPaid ? Number(o.total_amount || 0) : paidAmount);
                }, 0);

                archivedSummaryMap[s.id] = {
                    orderCount: validOrders.length,
                    revenue: rev
                };
            });
        }
    } catch (_) {}

    // Tải thông tin Merkle Root cho từng ca
    await Promise.all(
        currentArchivedShifts.map(async (s) => {
            try {
                const audit = await apiRequest(`/shifts/${s.id}/merkle-audit`);
                if (audit) archivedMerkleMap[s.id] = audit;
            } catch (_) {}
        })
    );
}

function filterAndRenderShifts() {
    const container = document.getElementById("archived-shifts-container");
    const countLabel = document.getElementById("archived-list-status-label");
    const searchVal = (document.getElementById("archive-search-shift")?.value || "").trim().toUpperCase();

    if (!container) return;

    let filtered = (currentArchivedShifts || []).filter((s) => {
        if (!searchVal) return true;
        const nameMatch = String(s.name || "").toUpperCase().includes(searchVal);
        const codeMatch = `CA-${String(s.id).padStart(4, "0")}`.includes(searchVal);
        return nameMatch || codeMatch;
    });

    // Cập nhật các chỉ số tổng hợp
    let totalRevenue = 0;
    let totalOrders = 0;
    filtered.forEach((s) => {
        const stat = archivedSummaryMap[s.id] || { revenue: 0, orderCount: 0 };
        totalRevenue += stat.revenue;
        totalOrders += stat.orderCount;
    });

    const elCount = document.getElementById("archived-stat-count");
    const elRev = document.getElementById("archived-stat-revenue");
    const elOrders = document.getElementById("archived-stat-orders");
    if (elCount) elCount.textContent = `${filtered.length} ca`;
    if (elRev) elRev.textContent = formatVND(totalRevenue);
    if (elOrders) elOrders.textContent = `${totalOrders} đơn`;

    if (countLabel) {
        countLabel.textContent = `Hiển thị ${filtered.length} ca trong kho`;
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 text-secondary bg-white rounded-4 border">
                <span class="d-block mb-2" style="font-size: 1.75rem;">📦</span>
                <strong>Chưa có ca làm việc nào trong kho lưu trữ.</strong>
                <p class="small text-secondary mb-0 mt-1">Khi bạn đóng ca và bấm "Lưu trữ" tại trang Ca làm việc, ca sẽ được niêm phong và lưu vào đây.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered
        .map((shift) => {
            const stats = archivedSummaryMap[shift.id] || { orderCount: 0, revenue: 0 };
            const targetRev = Number(shift.target_revenue || 5000000);
            const rev = stats.revenue;
            const orderCount = stats.orderCount;
            const pct = targetRev > 0 ? Math.min(100, Math.round((rev / targetRev) * 100)) : 0;

            const shiftCode = `CA-${String(shift.id).padStart(4, "0")}`;
            const timeRange = formatShiftRangeTime(shift.start_time, shift.end_time);
            const audit = archivedMerkleMap[shift.id] || null;
            const rootHash = (audit && audit.merkle_root) ? String(audit.merkle_root) : "Chưa lập chứng chỉ";
            const shortHash = rootHash.length > 20 ? `${rootHash.slice(0, 10)}...${rootHash.slice(-8)}` : rootHash;

            const archivedDateStr = shift.archived_at ? formatDateTime(shift.archived_at) : (shift.closed_at ? formatDateTime(shift.closed_at) : "—");

            return `
                <div class="shift-row-card is-closed">
                    <!-- Cột 1: Icon Kho + Tên ca + Badge Đã lưu trữ + Mã & Giờ -->
                    <div class="shift-col-info">
                        <div class="shift-icon-box is-closed">
                            ${getHeroicon("archive-box", "hi-icon")}
                        </div>
                        <div class="min-w-0">
                            <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                                <h3 class="shift-name mb-0 text-dark">${escapeHtml(shift.name)}</h3>
                                <span class="shift-status-pill is-closed">
                                    ● Đã lưu trữ
                                </span>
                            </div>
                            <div class="shift-code-time">
                                ${shiftCode} &nbsp;•&nbsp; ${timeRange}
                            </div>
                            <div class="text-secondary small mt-1" style="font-size: 0.73rem;">
                                Lưu trữ lúc: <strong>${archivedDateStr}</strong>
                            </div>
                        </div>
                    </div>

                    <!-- Cột 2: Doanh thu -->
                    <div class="shift-col-metric">
                        <span class="shift-metric-label">Doanh thu lưu trữ</span>
                        <div class="shift-metric-value font-numeric">${formatVND(rev)}</div>
                        <span class="shift-metric-sub">${pct}% mục tiêu</span>
                    </div>

                    <!-- Cột 3: Đơn hàng -->
                    <div class="shift-col-metric">
                        <span class="shift-metric-label">Đơn hàng</span>
                        <div class="shift-metric-value font-numeric">${orderCount}</div>
                        <span class="shift-metric-sub">đơn hoàn tất</span>
                    </div>

                    <!-- Cột 4: Con dấu Merkle Root Niêm phong -->
                    <div class="shift-col-metric" style="min-width: 170px;">
                        <span class="shift-metric-label d-flex align-items-center gap-1">
                            ${getHeroicon("shield-check", "hi-icon hi-icon-sm text-success")}
                            <span>Niêm phong Merkle</span>
                        </span>
                        <div class="fw-bold font-numeric text-dark mt-1" style="font-size: 0.78rem; letter-spacing: -0.01em;" title="${escapeHtml(rootHash)}">
                            <code>${escapeHtml(shortHash)}</code>
                        </div>
                        <button type="button" class="btn btn-link p-0 text-decoration-none small text-primary mt-0.5" style="font-size: 0.73rem;" onclick="viewMerkleAudit(${shift.id})">
                            Xem chứng chỉ kiểm toán →
                        </button>
                    </div>

                    <!-- Cột 5: Nút hành động -->
                    <div class="shift-col-actions">
                        <a href="dashboard.html?shift_id=${shift.id}" class="btn-shift-action-detail" title="Xem báo cáo đối soát &amp; sổ quỹ ca">
                            <span>Báo cáo ca</span>
                        </a>
                        <button type="button" class="btn-shift-action-detail" onclick="viewArchivedShiftDetail(${shift.id})" title="Xem chi tiết ca">
                            <span>Chi tiết</span>
                        </button>
                        <button type="button" class="btn btn-sm btn-light border text-secondary rounded-3 py-1.5 px-2.5" onclick="handleUnarchiveShift(${shift.id})" title="Đưa ca trở lại trang Ca làm việc">
                            <span>↩ Khôi phục</span>
                        </button>
                    </div>
                </div>
            `;
        })
        .join("");
}

function formatShiftRangeTime(startTime, endTime) {
    if (!startTime) return "--:--";
    const pad = (n) => String(n).padStart(2, "0");
    const d1 = new Date(startTime);
    const d2 = endTime ? new Date(endTime) : null;
    const t1 = `${pad(d1.getHours())}:${pad(d1.getMinutes())}`;
    const t2 = d2 ? `${pad(d2.getHours())}:${pad(d2.getMinutes())}` : "--:--";
    return `${t1} - ${t2}`;
}

async function viewMerkleAudit(shiftId) {
    const modalEl = document.getElementById("merkleAuditModal");
    const bodyEl = document.getElementById("merkle-modal-body");
    const nameEl = document.getElementById("merkle-modal-shift-name");
    if (!modalEl || !bodyEl) return;

    const shift = currentArchivedShifts.find((s) => Number(s.id) === Number(shiftId));
    if (nameEl) nameEl.textContent = shift ? `${shift.name} • CA-${String(shift.id).padStart(4, "0")}` : `Ca #${shiftId}`;

    bodyEl.innerHTML = `<div class="text-center py-4 text-secondary small">Đang nạp chứng chỉ Merkle Tree...</div>`;
    bootstrap.Modal.getOrCreateInstance(modalEl).show();

    try {
        const audit = await apiRequest(`/shifts/${shiftId}/merkle-audit`);
        if (!audit || !audit.merkle_root) {
            bodyEl.innerHTML = `
                <div class="alert alert-warning small mb-0">
                    Ca làm việc này chưa phát sinh hóa đơn hoặc chưa lưu chứng chỉ kiểm toán Merkle Root.
                </div>
            `;
            return;
        }

        const leaves = audit.leaf_hashes || [];
        bodyEl.innerHTML = `
            <div class="p-3 bg-light rounded-3 border mb-3">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <span class="small fw-semibold text-secondary">MERKLE ROOT HASH:</span>
                    <span class="fp-badge fp-badge-success">✓ ĐÃ NIÊM PHONG</span>
                </div>
                <div class="p-2 bg-white rounded border font-numeric text-break small fw-bold text-dark" style="font-size: 0.8rem;">
                    ${audit.merkle_root}
                </div>
                <div class="d-flex justify-content-between text-secondary small mt-2" style="font-size: 0.74rem;">
                    <span>Tổng số nút lá giao dịch: <strong>${leaves.length} đơn</strong></span>
                    <span>Niêm phong lúc: <strong>${formatDateTime(audit.audit_timestamp || audit.created_at)}</strong></span>
                </div>
            </div>

            <div class="small fw-semibold text-dark mb-1">Danh sách nút lá giao dịch (Leaf Hashes):</div>
            <div class="table-responsive border rounded-3" style="max-height: 200px; overflow-y: auto;">
                <table class="table table-sm table-hover mb-0" style="font-size: 0.76rem;">
                    <thead class="table-light">
                        <tr>
                            <th style="width: 15%;">Vị trí</th>
                            <th>Mã băm giao dịch</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${
                            leaves.length === 0
                                ? `<tr><td colspan="2" class="text-center py-3 text-secondary">Không có bút toán nào</td></tr>`
                                : leaves
                                      .map((h, idx) => `
                                    <tr>
                                        <td class="text-secondary font-numeric">Leaf #${idx}</td>
                                        <td class="font-numeric text-break">${h}</td>
                                    </tr>
                                `)
                                      .join("")
                        }
                    </tbody>
                </table>
            </div>

            <div class="d-flex justify-content-end mt-3">
                <button type="button" class="btn btn-sm btn-dark px-3 py-1.5 rounded-3" data-bs-dismiss="modal">
                    Đóng
                </button>
            </div>
        `;
    } catch (err) {
        bodyEl.innerHTML = `
            <div class="alert alert-danger small mb-0">
                Không thể tải thông tin kiểm toán Merkle: ${err.message || "Lỗi máy chủ"}
            </div>
        `;
    }
}

async function viewArchivedShiftDetail(shiftId) {
    const shift = currentArchivedShifts.find((s) => Number(s.id) === Number(shiftId));
    const modalEl = document.getElementById("archivedShiftDetailModal");
    const bodyEl = document.getElementById("archived-shift-detail-body");
    if (!modalEl || !bodyEl || !shift) return;

    bodyEl.innerHTML = `<div class="text-center py-4 text-secondary small">Đang tải số liệu đối soát của ca...</div>`;
    bootstrap.Modal.getOrCreateInstance(modalEl).show();

    let summary = null;
    try {
        summary = await apiRequest(`/dashboard/summary?shift_id=${encodeURIComponent(shift.id)}`);
    } catch (_) {
        summary = {};
    }

    bodyEl.innerHTML = `
        <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <strong class="fs-6 text-dark">${escapeHtml(shift.name)}</strong>
                <span class="fp-badge fp-badge-neutral">Đã lưu trữ</span>
            </div>
            <div class="small text-secondary">
                Bắt đầu: <strong>${formatDateTime(shift.start_time)}</strong> • Kết thúc: <strong>${formatDateTime(shift.end_time)}</strong>
                ${shift.closed_at ? `<br><span class="text-danger">Đóng ca: <strong>${formatDateTime(shift.closed_at)}</strong></span>` : ""}
                ${shift.archived_at ? `<br><span class="text-primary">Lưu trữ: <strong>${formatDateTime(shift.archived_at)}</strong></span>` : ""}
            </div>
        </div>

        <div class="p-3 bg-light rounded-3 border mb-3">
            <div class="row g-2 text-center">
                <div class="col-6">
                    <span class="d-block small text-secondary">Hóa đơn hợp lệ</span>
                    <strong class="font-numeric fs-6 text-dark">${formatVND(summary.valid_order_total || 0)}</strong>
                </div>
                <div class="col-6">
                    <span class="d-block small text-secondary">Thực thu ngân hàng</span>
                    <strong class="font-numeric fs-6 text-success">${formatVND(summary.allocated_payment_total || 0)}</strong>
                </div>
            </div>
        </div>

        <div class="d-flex justify-content-end gap-2">
            <a href="dashboard.html?shift_id=${shift.id}" class="btn-shift-create py-1.5 px-3" style="height: auto; font-size: 0.82rem;">
                Mở báo cáo đầy đủ →
            </a>
        </div>
    `;
}

async function handleUnarchiveShift(shiftId) {
    const shift = currentArchivedShifts.find((s) => Number(s.id) === Number(shiftId));
    const shiftName = shift ? shift.name : `Ca #${shiftId}`;

    if (!confirm(`Bạn có chắc chắn muốn khôi phục "${shiftName}" trở lại trang Ca làm việc không?`)) {
        return;
    }

    try {
        await apiRequest(`/shifts/${shiftId}/unarchive`, {
            method: "POST"
        });
        showToast(`Đã khôi phục "${shiftName}" trở lại trang Ca làm việc thành công.`, "success");
        loadArchivedShifts(false);
    } catch (err) {
        showToast(err.message || "Không thể khôi phục ca làm việc.", "danger");
    }
}
