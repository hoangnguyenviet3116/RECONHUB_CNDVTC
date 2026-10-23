// ==========================================================================
// QUẢN LÝ CA BÁN HÀNG (frontend/js/shifts.js)
// ==========================================================================

let currentShiftsList = [];
let isSubmittingShift = false;

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

    loadShifts(false);
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
        showToast("Đã cập nhật danh sách ca bán hàng.", "success");
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
                <button type="button" class="btn-fp-dark mt-2" data-bs-toggle="modal" data-bs-target="#openShiftModal">
                    + Mở ca bán hàng mới
                </button>
            </div>
        `;
        return;
    }

    bannerEl.innerHTML = `
        <div class="recon-workspace-card" style="background: linear-gradient(135deg, #ffffff 0%, #ecfdf5 100%); border: 1.5px solid #10b981;">
            <div class="row align-items-center g-3">
                <div class="col-12 col-md-8">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <span class="fp-badge fp-badge-success">● Ca đang mở bán</span>
                        <span class="small text-secondary">Mã ca #${openShift.id}</span>
                    </div>
                    <h1 class="h4 fw-bold mb-1">${escapeHtml(openShift.name)}</h1>
                    <div class="text-secondary small">
                        Giờ mở ca: <strong>${formatDateTime(openShift.start_time)}</strong> • Doanh thu mục tiêu: <strong class="text-dark font-numeric">${formatVND(openShift.target_revenue)}</strong>
                    </div>
                </div>
                <div class="col-12 col-md-4 text-md-end">
                    <a href="pos.html?shift_id=${openShift.id}" class="btn-fp-success w-100 w-md-auto py-2 px-4">
                        <span>Mở quầy thu ngân</span>
                        ${getHeroicon("arrow-right", "hi-icon")}
                    </a>
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
            return `
                <div class="col-12 col-md-6">
                    <div class="kpi-metric-card ${isOpen ? "kpi-border-emerald" : "kpi-border-cyan bg-light"}">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="small text-secondary fw-semibold">Mã ca #${shift.id}</span>
                            ${renderStatusBadge(shift.status)}
                        </div>
                        <h3 class="h6 fw-bold mb-2">${escapeHtml(shift.name)}</h3>
                        <div class="small text-secondary mb-3">
                            Doanh thu mục tiêu: <strong class="text-dark font-numeric">${formatVND(shift.target_revenue)}</strong><br>
                            Thời gian: ${formatDateTime(shift.start_time)} → ${formatDateTime(shift.end_time)}
                        </div>
                        <div class="d-flex justify-content-between align-items-center pt-2 border-top">
                            <button type="button" class="btn-fp-outline py-1 px-3" style="font-size:0.8rem;" onclick="viewShiftDetail(${shift.id})">
                                Chi tiết ca
                            </button>
                            ${
                                isOpen
                                    ? `<a href="pos.html?shift_id=${shift.id}" class="btn-fp-dark py-1 px-3" style="font-size:0.8rem;">
                                           Quầy thu ngân →
                                       </a>`
                                    : `<a href="dashboard.html?shift_id=${shift.id}" class="btn-fp-outline py-1 px-3" style="font-size:0.8rem;">
                                           Báo cáo ca
                                       </a>`
                            }
                        </div>
                    </div>
                </div>
            `;
        })
        .join("");
}

function viewShiftDetail(shiftId) {
    const shift = currentShiftsList.find((s) => Number(s.id) === Number(shiftId)) || currentShiftsList[0];
    const store = getDemoStore();
    const summary = computeStoreSummary(store);

    const bodyEl = document.getElementById("shift-detail-body");
    if (!bodyEl || !shift) return;

    bodyEl.innerHTML = `
        <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <strong class="fs-6">${escapeHtml(shift.name)}</strong>
                ${renderStatusBadge(shift.status)}
            </div>
            <div class="small text-secondary">Giờ mở: ${formatDateTime(shift.start_time)}</div>
        </div>
        <div class="p-3 rounded-4 bg-light border small">
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Mục tiêu doanh thu:</span>
                <strong class="font-numeric">${formatVND(shift.target_revenue)}</strong>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Tổng hóa đơn trong ca:</span>
                <strong class="text-primary font-numeric">${formatVND(summary.valid_order_total)}</strong>
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

    const modalEl = document.getElementById("shiftDetailModal");
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
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

    if (!name || targetRevenue <= 0 || !startTime || !endTime || new Date(endTime) <= new Date(startTime)) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập đầy đủ tên ca, doanh thu > 0 và giờ kết thúc hợp lệ.";
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
                start_time: new Date(startTime).toISOString(),
                end_time: new Date(endTime).toISOString(),
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
                status: "OPEN"
            });
            saveDemoStore(store);
        } else {
            if (errorBox) {
                errorBox.textContent = err.message;
                errorBox.classList.remove("d-none");
            }
            isSubmittingShift = false;
            return;
        }
    }

    isSubmittingShift = false;
    const modalEl = document.getElementById("openShiftModal");
    if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
    showToast(`Đã mở ca bán hàng: ${name}`, "success");
    loadShifts(false);
}

function escapeHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}