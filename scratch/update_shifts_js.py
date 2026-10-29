# -*- coding: utf-8 -*-

new_shifts_js = """// ==========================================================================
// QUẢN LÝ CA BÁN HÀNG — VIETQR RECONHUB (frontend/js/shifts.js)
// Giao diện phong cách Fintech SaaS Hiện đại (Chuẩn Thẻ Nằm Ngang & Form Nhanh)
// ==========================================================================

let currentShiftsList = [];
let shiftsSummaryMap = {};
let currentStatusFilter = "ALL";
let isSubmittingShift = false;
let isClosingShift = false;
let pendingShiftIdToClose = null;
let shiftsPollingTimer = null;

function initShiftsPage() {
    setDefaultShiftFormTimes();

    const refreshBtn = document.getElementById("btn-refresh-shifts");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => loadShifts(true));
    }

    const openShiftForm = document.getElementById("open-shift-form");
    if (openShiftForm) {
        openShiftForm.addEventListener("submit", handleCreateShiftSubmit);
    }

    const confirmCloseBtn = document.getElementById("btn-confirm-close-shift");
    if (confirmCloseBtn) {
        confirmCloseBtn.addEventListener("click", handleConfirmCloseShift);
    }

    const filterSelect = document.getElementById("filter-shift-status");
    if (filterSelect) {
        filterSelect.addEventListener("change", (e) => {
            currentStatusFilter = e.target.value;
            renderShiftsList(currentShiftsList);
        });
    }

    loadShifts(false);
    startShiftsPolling();
}

function setDefaultShiftFormTimes() {
    const startInput = document.getElementById("shift-start-time");
    const endInput = document.getElementById("shift-end-time");
    const nameInput = document.getElementById("shift-name");

    const now = new Date();
    const later = new Date(now.getTime() + 6 * 60 * 60 * 1000);
    const toLocalISO = (d) => {
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    if (startInput && !startInput.value) startInput.value = toLocalISO(now);
    if (endInput && !endInput.value) endInput.value = toLocalISO(later);

    if (nameInput && (!nameInput.value || nameInput.value.includes("24/10/2026"))) {
        const dayNames = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
        const h = now.getHours();
        const period = h < 12 ? "Ca sáng" : (h < 18 ? "Ca chiều" : "Ca tối");
        nameInput.value = `${period} — ${dayNames[now.getDay()]}`;
    }
}

function startShiftsPolling() {
    if (shiftsPollingTimer) clearInterval(shiftsPollingTimer);
    shiftsPollingTimer = setInterval(() => {
        if (document.hidden) return;
        loadShifts(false);
    }, 5000);
}

async function loadShifts(showNotification = false) {
    try {
        const data = await apiRequest("/shifts");
        currentShiftsList = Array.isArray(data) ? data : (data.items || data.shifts || []);
    } catch (_) {
        const store = getDemoStore();
        currentShiftsList = store.shifts || [];
    }

    // Tải số liệu doanh thu và số đơn tương ứng của từng ca từ dashboard summary
    await fetchShiftsSummaryStats();

    renderActiveShiftHero(currentShiftsList);
    renderShiftsList(currentShiftsList);

    if (showNotification) {
        showToast("Đã cập nhật danh sách ca bán hàng mới nhất.", "success");
    }
}

async function fetchShiftsSummaryStats() {
    shiftsSummaryMap = {};
    try {
        const summaryData = await apiRequest("/dashboard/summary?shift_id=ALL");
        if (summaryData && Array.isArray(summaryData.orders)) {
            const orders = summaryData.orders;
            (currentShiftsList || []).forEach((s) => {
                const sOrders = orders.filter((o) => Number(o.shift_id) === Number(s.id));
                const validOrders = sOrders.filter(
                    (o) => !["CANCELLED_ORDER"].includes(String(o.order_status || o.status || "").toUpperCase())
                );
                const rev = validOrders.reduce((sum, o) => {
                    const isPaid = String(o.payment_status).toUpperCase() === "PAID";
                    const paidAmount = Number(o.paid_amount || o.allocated_amount || 0);
                    return sum + (isPaid ? Number(o.total_amount || 0) : paidAmount);
                }, 0);

                shiftsSummaryMap[s.id] = {
                    orderCount: validOrders.length,
                    revenue: rev
                };
            });
        }
    } catch (_) {
        try {
            const store = getDemoStore();
            const orders = store.orders || [];
            (currentShiftsList || []).forEach((s) => {
                const sOrders = orders.filter((o) => Number(o.shift_id) === Number(s.id));
                const validOrders = sOrders.filter(
                    (o) => !["CANCELLED_ORDER"].includes(String(o.order_status || "").toUpperCase())
                );
                const rev = validOrders.reduce((sum, o) => {
                    const isPaid = String(o.payment_status).toUpperCase() === "PAID";
                    const paidAmount = Number(o.paid_amount || 0);
                    return sum + (isPaid ? Number(o.total_amount || 0) : paidAmount);
                }, 0);

                shiftsSummaryMap[s.id] = {
                    orderCount: validOrders.length,
                    revenue: rev
                };
            });
        } catch (e) {}
    }
}

function renderActiveShiftHero(shifts) {
    const bannerEl = document.getElementById("active-shift-banner");
    if (!bannerEl) return;

    const openShift = (shifts || []).find((s) => String(s.status).toUpperCase() === "OPEN");

    if (!openShift) {
        bannerEl.innerHTML = `
            <div class="alert alert-light border py-3 px-4 rounded-4 small text-secondary d-flex align-items-center gap-3 mb-4" style="background:#ffffff; border-color:#eef2f6 !important;">
                <span style="font-size: 1.25rem;">💡</span>
                <div>
                    <strong class="text-dark">Chưa có ca làm việc nào đang mở.</strong>
                    <span>Bạn hãy nhập thông tin ở ô trên và nhấn <strong>Tạo ca mới</strong> để nhân viên có thể bắt đầu tạo đơn tại quầy.</span>
                </div>
            </div>
        `;
    } else {
        // Nếu đã có ca đang mở, ca này sẽ hiển thị nổi bật ở vị trí đầu danh sách bên dưới (với viền xanh lá đặc trưng)
        bannerEl.innerHTML = "";
    }
}

function renderShiftsList(shifts) {
    const container = document.getElementById("shifts-container");
    const countLabel = document.getElementById("shifts-count-label");
    if (!container) return;

    const totalCount = (shifts || []).length;
    if (countLabel) {
        countLabel.textContent = `${totalCount} ca gần nhất`;
    }

    if (!shifts || shifts.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 text-secondary bg-white rounded-4 border">
                Chưa có ca làm việc nào trong hệ thống. Hãy tạo ca đầu tiên ở trên!
            </div>
        `;
        return;
    }

    // Lọc theo trạng thái
    let filtered = [...shifts];
    if (currentStatusFilter === "OPEN") {
        filtered = filtered.filter((s) => String(s.status).toUpperCase() === "OPEN");
    } else if (currentStatusFilter === "CLOSED") {
        filtered = filtered.filter((s) => String(s.status).toUpperCase() === "CLOSED");
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 text-secondary bg-white rounded-4 border">
                Không tìm thấy ca làm việc nào phù hợp với bộ lọc "${currentStatusFilter === "OPEN" ? "Đang mở" : "Đã đóng"}".
            </div>
        `;
        return;
    }

    container.innerHTML = filtered
        .map((shift) => {
            const isOpen = String(shift.status).toUpperCase() === "OPEN";
            const stats = shiftsSummaryMap[shift.id] || { orderCount: 0, revenue: 0 };
            const targetRev = Number(shift.target_revenue || 15000000);
            const rev = stats.revenue;
            const orderCount = stats.orderCount;
            const pct = targetRev > 0 ? Math.min(100, Math.round((rev / targetRev) * 100)) : 0;

            const shiftCode = `CA-${String(shift.id).padStart(4, "0")}`;
            const timeRange = formatShiftRangeTime(shift.start_time, shift.end_time);

            return `
                <div class="shift-row-card ${isOpen ? "is-open" : "is-closed"}">
                    <!-- Cột 1: Icon + Tên ca + Badge Trạng thái + Mã & Giờ -->
                    <div class="shift-col-info">
                        <div class="shift-icon-box ${isOpen ? "is-open" : "is-closed"}">
                            ${isOpen ? getHeroicon("clock", "hi-icon") : getHeroicon("lock-closed", "hi-icon")}
                        </div>
                        <div class="min-w-0">
                            <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                                <h3 class="shift-name mb-0 text-dark">${escapeHtml(shift.name)}</h3>
                                <span class="shift-status-pill ${isOpen ? "is-open" : "is-closed"}">
                                    ● ${isOpen ? "Đang mở" : "Đã đóng"}
                                </span>
                            </div>
                            <div class="shift-code-time">
                                ${shiftCode} &nbsp;•&nbsp; ${timeRange}
                            </div>
                        </div>
                    </div>

                    <!-- Cột 2: Doanh thu -->
                    <div class="shift-col-metric">
                        <span class="shift-metric-label">Doanh thu</span>
                        <div class="shift-metric-value font-numeric">${formatVND(rev)}</div>
                        <span class="shift-metric-sub">${pct}% mục tiêu</span>
                    </div>

                    <!-- Cột 3: Đơn hàng -->
                    <div class="shift-col-metric">
                        <span class="shift-metric-label">Đơn hàng</span>
                        <div class="shift-metric-value font-numeric">${orderCount}</div>
                        <span class="shift-metric-sub">đơn hợp lệ</span>
                    </div>

                    <!-- Cột 4: Tiến độ -->
                    <div class="shift-col-progress">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="shift-metric-label mb-0">Tiến độ</span>
                            <span class="shift-progress-percent font-numeric">${pct}%</span>
                        </div>
                        <div class="shift-progress-track">
                            <div class="shift-progress-fill" style="width: ${pct}%;"></div>
                        </div>
                    </div>

                    <!-- Cột 5: Nút hành động -->
                    <div class="shift-col-actions">
                        <a href="pos.html?shift_id=${shift.id}" class="btn-shift-action-pos" title="Đến quầy thu ngân của ca này">
                            <span>→ Đến quầy thu ngân</span>
                        </a>
                        ${
                            isOpen
                                ? `
                            <button type="button" class="btn-shift-action-close" onclick="openCloseShiftConfirmModal(${shift.id})" title="Đóng ca và niêm phong Merkle Root">
                                ${getHeroicon("lock-closed", "hi-icon")}
                                <span>Đóng ca</span>
                            </button>
                        `
                                : `
                            <a href="dashboard.html?shift_id=${shift.id}" class="btn-shift-action-detail" title="Xem báo cáo đối soát &amp; sổ quỹ ca">
                                <span>Báo cáo ca</span>
                            </a>
                            <button type="button" class="btn-shift-action-detail" onclick="viewShiftDetail(${shift.id})" title="Xem chi tiết bút toán">
                                <span>Chi tiết</span>
                            </button>
                        `
                        }
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

function openCloseShiftConfirmModal(shiftId) {
    const role = getCurrentRole();
    if (role !== "OWNER") {
        showToast("Chỉ tài khoản Chủ cửa hàng (OWNER) mới có quyền đóng ca làm việc.", "danger");
        return;
    }

    const shift = currentShiftsList.find((s) => Number(s.id) === Number(shiftId));
    if (!shift) {
        showToast("Không tìm thấy thông tin ca làm việc.", "danger");
        return;
    }

    if (String(shift.status).toUpperCase() === "CLOSED") {
        showToast("Ca làm việc này đã được đóng trước đó.", "warning");
        return;
    }

    pendingShiftIdToClose = shift.id;
    const nameEl = document.getElementById("modal-close-shift-name");
    const idEl = document.getElementById("modal-close-shift-id");
    const errEl = document.getElementById("close-shift-error");

    if (nameEl) nameEl.textContent = shift.name;
    if (idEl) idEl.textContent = String(shift.id);
    if (errEl) errEl.classList.add("d-none");

    const modalEl = document.getElementById("confirmCloseShiftModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

async function handleConfirmCloseShift() {
    if (isClosingShift || !pendingShiftIdToClose) return;

    const errorBox = document.getElementById("close-shift-error");
    if (errorBox) errorBox.classList.add("d-none");

    isClosingShift = true;
    try {
        await apiRequest(`/shifts/${pendingShiftIdToClose}/close`, {
            method: "POST"
        });

        isClosingShift = false;
        const modalEl = document.getElementById("confirmCloseShiftModal");
        if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();

        showToast("Đã đóng ca và niêm phong Cây Merkle thành công. Quầy thu ngân đã khóa nhận đơn mới.", "success");
        loadShifts(false);
    } catch (err) {
        isClosingShift = false;
        const msg = err.message || "Không thể đóng ca làm việc.";
        if (errorBox) {
            errorBox.textContent = msg;
            errorBox.classList.remove("d-none");
        }
        showToast(msg, "danger");
    }
}

async function viewShiftDetail(shiftId) {
    const shift = currentShiftsList.find((s) => Number(s.id) === Number(shiftId)) || currentShiftsList[0];
    const bodyEl = document.getElementById("shift-detail-body");
    if (!bodyEl || !shift) return;

    bodyEl.innerHTML = `<div class="text-center py-4 text-secondary small">Đang tải số liệu đối soát của ca...</div>`;
    const modalEl = document.getElementById("shiftDetailModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();

    let summary = null;
    try {
        summary = await apiRequest(`/dashboard/summary?shift_id=${encodeURIComponent(shift.id)}`);
    } catch (_) {
        const store = getDemoStore();
        summary = computeStoreSummary(store, shift.id);
    }

    bodyEl.innerHTML = `
        <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <strong class="fs-6 text-dark">${escapeHtml(shift.name)}</strong>
                ${renderStatusBadge(shift.status)}
            </div>
            <div class="small text-secondary">
                Bắt đầu: <strong>${formatDateTime(shift.start_time)}</strong> • Kết thúc: <strong>${formatDateTime(shift.end_time)}</strong>
                ${shift.closed_at ? `<br><span class="text-danger">Đã đóng lúc: <strong>${formatDateTime(shift.closed_at)}</strong></span>` : ""}
            </div>
        </div>
        <div class="p-3 rounded-4 bg-light border small">
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Mục tiêu doanh thu:</span>
                <strong class="font-numeric">${formatVND(shift.target_revenue)}</strong>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Tổng hóa đơn hợp lệ:</span>
                <strong class="text-primary font-numeric">${formatVND(summary.valid_order_total)} (${summary.valid_order_count ?? 0} đơn)</strong>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Đã thu khớp đơn:</span>
                <strong class="text-success font-numeric">${formatVND(summary.allocated_payment_total)}</strong>
            </div>
            <div class="d-flex justify-content-between pt-1">
                <span class="text-secondary">Còn chờ thu:</span>
                <strong class="text-warning font-numeric">${formatVND(summary.remaining_receivable)}</strong>
            </div>
        </div>
    `;
}

async function handleCreateShiftSubmit(event) {
    event.preventDefault();
    if (isSubmittingShift) return;

    const name = (document.getElementById("shift-name")?.value || "").trim();
    const targetRevenue = Number(document.getElementById("target-revenue")?.value || 0);
    const startTime = document.getElementById("shift-start-time")?.value || "";
    const endTime = document.getElementById("shift-end-time")?.value || "";
    const errorBox = document.getElementById("open-shift-error");

    if (errorBox) errorBox.classList.add("d-none");

    if (!name) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập tên ca bán hàng.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    if (!Number.isFinite(targetRevenue) || targetRevenue <= 0) {
        if (errorBox) {
            errorBox.textContent = "Mục tiêu doanh thu ca phải lớn hơn 0 VNĐ.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    if (!startTime || !endTime) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng thiết lập đầy đủ thời gian bắt đầu và kết thúc ca.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    const startDate = new Date(startTime);
    const endDate = new Date(endTime);

    if (endDate <= startDate) {
        if (errorBox) {
            errorBox.textContent = "Thời gian kết thúc ca phải sau thời gian bắt đầu ca.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    isSubmittingShift = true;
    try {
        await apiRequest("/shifts", {
            method: "POST",
            body: JSON.stringify({
                merchant_id: getCurrentMerchantId(),
                name,
                target_revenue: targetRevenue,
                start_time: startTime,
                end_time: endTime,
                status: "OPEN"
            })
        });
    } catch (err) {
        if (err.isNetworkError) {
            const store = getDemoStore();
            store.shifts.unshift({
                id: store.shifts.length + 1,
                merchant_id: 1,
                name,
                target_revenue: targetRevenue,
                start_time: startTime,
                end_time: endTime,
                status: "OPEN",
                closed_at: null
            });
            saveDemoStore(store);
        } else {
            if (errorBox) {
                errorBox.textContent = err.message || "Không thể tạo ca làm việc.";
                errorBox.classList.remove("d-none");
            }
            isSubmittingShift = false;
            return;
        }
    }

    isSubmittingShift = false;
    const modalEl = document.getElementById("openShiftModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
    showToast(`Đã mở ca bán hàng mới: ${name}`, "success");
    loadShifts(false);
}

function escapeHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
"""

with open("frontend/js/shifts.js", "w", encoding="utf-8") as f:
    f.write(new_shifts_js)

print("Updated frontend/js/shifts.js successfully.")
