// ==========================================================================
// QUẢN LÝ CA BÁN HÀNG (frontend/js/shifts.js)
// ==========================================================================

let currentShiftsList = [];
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

    loadShifts(false);
    startShiftsPolling();
}

function setDefaultShiftFormTimes() {
    const startInput = document.getElementById("shift-start-time");
    const endInput = document.getElementById("shift-end-time");
    if (!startInput || !endInput) return;

    const now = new Date();
    const later = new Date(now.getTime() + 8 * 60 * 60 * 1000);
    const toLocalISO = (d) => {
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    startInput.value = toLocalISO(now);
    endInput.value = toLocalISO(later);
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

    renderActiveShiftHero(currentShiftsList);
    renderShiftsList(currentShiftsList);

    if (showNotification) {
        showToast("Đã cập nhật danh sách ca bán hàng mới nhất.", "success");
    }
}

function renderActiveShiftHero(shifts) {
    const bannerEl = document.getElementById("active-shift-banner");
    if (!bannerEl) return;

    const openShift = (shifts || []).find((s) => String(s.status).toUpperCase() === "OPEN");

    if (!openShift) {
        bannerEl.innerHTML = `
            <div class="recon-workspace-card text-center py-4">
                <span class="fp-badge fp-badge-warning mb-2">Chưa mở ca</span>
                <h1 class="h5 fw-bold mb-2">Hiện chưa có ca bán hàng nào đang mở</h1>
                <p class="text-secondary small mb-3">Vui lòng mở ca làm việc mới để nhân viên có thể tạo đơn hàng tại Quầy thu ngân.</p>
                <button type="button" class="btn-fp-dark" data-bs-toggle="modal" data-bs-target="#openShiftModal">
                    + Mở ca bán hàng mới
                </button>
            </div>
        `;
        return;
    }

    bannerEl.innerHTML = `
        <div class="recon-workspace-card" style="background: linear-gradient(135deg, #ffffff 0%, #ecfdf5 100%); border: 1.5px solid #10b981;">
            <div class="row align-items-center g-3">
                <div class="col-12 col-lg-7">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <span class="fp-badge fp-badge-success">● Ca đang mở bán</span>
                        <span class="small text-secondary">Mã ca #${openShift.id}</span>
                    </div>
                    <h1 class="h4 fw-bold mb-1 text-dark">${escapeHtml(openShift.name)}</h1>
                    <div class="text-secondary small mt-2">
                        <div>Bắt đầu: <strong class="text-dark">${formatDateTime(openShift.start_time)}</strong> • Kết thúc dự kiến: <strong class="text-primary">${formatDateTime(openShift.end_time)}</strong></div>
                        <div class="mt-1">Mục tiêu doanh thu: <strong class="text-dark font-numeric">${formatVND(openShift.target_revenue)}</strong></div>
                    </div>
                </div>
                <div class="col-12 col-lg-5 text-lg-end d-flex flex-wrap gap-2 justify-content-lg-end">
                    <a href="pos.html?shift_id=${openShift.id}" class="btn-fp-success py-2 px-3" style="font-size:0.86rem;">
                        <span>Mở quầy thu ngân</span>
                        ${getHeroicon("arrow-right", "hi-icon")}
                    </a>
                    <button type="button" class="btn-fp-danger py-2 px-3" style="font-size:0.86rem;" onclick="openCloseShiftConfirmModal(${openShift.id})">
                        <span>Đóng ca làm việc</span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderShiftsList(shifts) {
    const container = document.getElementById("shifts-container");
    if (!container) return;

    if (!shifts || shifts.length === 0) {
        container.innerHTML = `<div class="col-12 text-center py-4 text-secondary">Chưa có ca làm việc nào.</div>`;
        return;
    }

    container.innerHTML = shifts
        .map((shift) => {
            const isOpen = String(shift.status).toUpperCase() === "OPEN";
            const isClosed = String(shift.status).toUpperCase() === "CLOSED";

            return `
                <div class="col-12 col-md-6">
                    <div class="kpi-metric-card ${isOpen ? "kpi-border-emerald" : "kpi-border-cyan bg-light"}">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="small text-secondary fw-semibold">Mã ca #${shift.id}</span>
                            ${renderStatusBadge(shift.status)}
                        </div>
                        <h3 class="h6 fw-bold mb-2 text-dark">${escapeHtml(shift.name)}</h3>
                        <div class="small text-secondary mb-3">
                            <div>Mục tiêu doanh thu: <strong class="text-dark font-numeric">${formatVND(shift.target_revenue)}</strong></div>
                            <div class="mt-1">Bắt đầu: <strong>${formatDateTime(shift.start_time)}</strong></div>
                            <div>Kết thúc dự kiến: <strong class="${isOpen ? "text-primary" : "text-dark"}">${formatDateTime(shift.end_time)}</strong></div>
                            ${
                                shift.closed_at
                                    ? `<div class="text-danger mt-1">Đã đóng thực tế lúc: <strong>${formatDateTime(shift.closed_at)}</strong></div>`
                                    : ""
                            }
                        </div>
                        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 pt-2 border-top">
                            <button type="button" class="btn-fp-outline py-1 px-2" style="font-size:0.78rem;" onclick="viewShiftDetail(${shift.id})">
                                Chi tiết ca
                            </button>
                            <div class="d-flex gap-1">
                                ${
                                    isOpen
                                        ? `
                                            <a href="pos.html?shift_id=${shift.id}" class="btn-fp-dark py-1 px-2" style="font-size:0.78rem;">
                                                Quầy thu ngân →
                                            </a>
                                            <button type="button" class="btn-fp-danger py-1 px-2" style="font-size:0.78rem;" onclick="openCloseShiftConfirmModal(${shift.id})">
                                                Đóng ca
                                            </button>
                                        `
                                        : `
                                            <a href="pos.html?shift_id=${shift.id}" class="btn-fp-outline py-1 px-2" style="font-size:0.78rem;" title="Xem quầy thu ngân của ca này">
                                                Quầy thu ngân
                                            </a>
                                            <a href="dashboard.html?shift_id=${shift.id}" class="btn-fp-outline py-1 px-2" style="font-size:0.78rem;">
                                                Báo cáo ca
                                            </a>
                                            <button type="button" class="btn btn-sm btn-light border text-muted py-1 px-2" disabled style="font-size:0.75rem;">
                                                Đã đóng
                                            </button>
                                        `
                                }
                            </div>
                        </div>
                    </div>
                </div>
            `;
        })
        .join("");
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

        showToast("Đã đóng ca làm việc thành công. Quầy thu ngân đã bị vô hiệu hóa.", "success");
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
