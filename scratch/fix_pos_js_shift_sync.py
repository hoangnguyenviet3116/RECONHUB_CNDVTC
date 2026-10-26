# -*- coding: utf-8 -*-
"""
Fix pos.js so clicking 'Đến quầy thu ngân' from any shift on index.html
strictly selects that exact shift on pos.html (both form and table filter).
"""

with open("frontend/js/pos.js", "r", encoding="utf-8") as f:
    pos_js = f.read()

# 1. Update initPosPage to await shifts before loading orders
old_init = """// 1. Khởi tạo màn hình Quầy thu ngân
function initPosPage() {
    bindPosEvents();
    loadOpenShiftsForPos();
    loadPosOrders(false);
    startPosPolling();

    // Lắng nghe sự kiện khi khách bấm chuyển khoản ở Tab Cổng thanh toán
    window.addEventListener("storage", (event) => {
        if (event.key === DEMO_STORE_KEY) {
            loadPosOrders(false, true);
        }
    });
}"""

new_init = """// 1. Khởi tạo màn hình Quầy thu ngân
async function initPosPage() {
    bindPosEvents();
    // Bắt buộc tải và chọn đúng ca từ URL (?shift_id=...) trước khi tải bảng hóa đơn
    await loadOpenShiftsForPos();
    await loadPosOrders(false);
    startPosPolling();

    // Lắng nghe sự kiện khi khách bấm chuyển khoản ở Tab Cổng thanh toán
    window.addEventListener("storage", (event) => {
        if (event.key === DEMO_STORE_KEY) {
            loadPosOrders(false, true);
        }
    });
}"""

assert old_init in pos_js, "old_init not found"
pos_js = pos_js.replace(old_init, new_init, 1)

# 2. Update bindPosEvents so changing either select syncs with the other and re-renders table
old_bind_selects = """    const formShiftSelect = document.getElementById("pos-shift-select");
    if (formShiftSelect) {
        formShiftSelect.addEventListener("change", () => {
            updatePosShiftLockState();
        });
    }

    const shiftFilterSelect = document.getElementById("pos-filter-shift");
    if (shiftFilterSelect) {
        shiftFilterSelect.addEventListener("change", (e) => {
            if (formShiftSelect && e.target.value !== "ALL") {
                formShiftSelect.value = e.target.value;
                updatePosShiftLockState();
            }
            renderPosOrdersTable(posOrdersCache);
        });
    }"""

new_bind_selects = """    const formShiftSelect = document.getElementById("pos-shift-select");
    const shiftFilterSelect = document.getElementById("pos-filter-shift");

    if (formShiftSelect) {
        formShiftSelect.addEventListener("change", (e) => {
            const val = e.target.value;
            if (shiftFilterSelect && val) {
                shiftFilterSelect.value = val;
            }
            updatePosShiftLockState();
            renderPosOrdersTable(posOrdersCache);
        });
    }

    if (shiftFilterSelect) {
        shiftFilterSelect.addEventListener("change", (e) => {
            const val = e.target.value;
            if (formShiftSelect && val !== "ALL") {
                formShiftSelect.value = val;
            }
            updatePosShiftLockState();
            renderPosOrdersTable(posOrdersCache);
        });
    }"""

assert old_bind_selects in pos_js, "old_bind_selects not found"
pos_js = pos_js.replace(old_bind_selects, new_bind_selects, 1)

# 3. Update loadOpenShiftsForPos to prioritize preferredShiftId above all else
old_load_shifts = """// 3. Tải danh sách ca đang mở bán và đồng bộ bộ lọc ca
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

    posShiftsCache = shifts;

    const openShifts = shifts.filter((s) => String(s.status || "").toUpperCase() === "OPEN");
    const currentSelectedVal = selectEl?.value;

    if (selectEl) {
        if (shifts.length === 0) {
            selectEl.innerHTML = '<option value="">Không có ca làm việc</option>';
        } else {
            // Cho phép chọn các ca, ưu tiên ca đang mở
            const defaultShiftId = preferredShiftId || currentSelectedVal || (openShifts[0] ? String(openShifts[0].id) : String(shifts[0].id));
            selectEl.innerHTML = shifts
                .map((s) => {
                    const isOpen = String(s.status).toUpperCase() === "OPEN";
                    const isSelected = String(s.id) === String(defaultShiftId) ? "selected" : "";
                    const statusTag = isOpen ? "(Đang mở)" : "(Đã đóng)";
                    return `<option value="${s.id}" ${isSelected}>Ca ${s.id}: ${escapePosHtml(s.name)} ${statusTag}</option>`;
                })
                .join("");
        }
    }

    if (filterShiftEl && shifts.length > 0) {
        const curFilterVal = filterShiftEl.value;
        const defaultFilterShift = curFilterVal || preferredShiftId || (openShifts[0] ? String(openShifts[0].id) : "1");
        let html = '<option value="ALL">Tất cả ca bán hàng</option>';
        shifts.forEach((s) => {
            const statusLabel = String(s.status).toUpperCase() === "OPEN" ? "(Đang mở)" : "(Đã đóng)";
            const isSelected = String(s.id) === defaultFilterShift ? "selected" : "";
            html += `<option value="${s.id}" ${isSelected}>Ca ${s.id}: ${escapePosHtml(s.name)} ${statusLabel}</option>`;
        });
        filterShiftEl.innerHTML = html;
    }

    updatePosShiftLockState();
}"""

new_load_shifts = """// 3. Tải danh sách ca đang mở bán và đồng bộ chính xác ca được chỉ định từ URL
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

    posShiftsCache = shifts;

    const openShifts = shifts.filter((s) => String(s.status || "").toUpperCase() === "OPEN");

    // Xác định ca cần chọn:
    // 1. Ưu tiên số 1: Tham số shift_id truyền từ URL (?shift_id=2)
    // 2. Ưu tiên số 2: Ca đang mở mới nhất
    // 3. Ưu tiên số 3: Ca đầu tiên trong danh sách
    let targetShiftId = null;

    if (preferredShiftId && (preferredShiftId === "ALL" || shifts.some((s) => String(s.id) === String(preferredShiftId)))) {
        targetShiftId = preferredShiftId;
    } else if (openShifts.length > 0) {
        targetShiftId = String(openShifts[0].id);
    } else if (shifts.length > 0) {
        targetShiftId = String(shifts[0].id);
    }

    if (selectEl) {
        if (shifts.length === 0) {
            selectEl.innerHTML = '<option value="">Không có ca làm việc</option>';
        } else {
            selectEl.innerHTML = shifts
                .map((s) => {
                    const isOpen = String(s.status).toUpperCase() === "OPEN";
                    const isSelected = String(s.id) === String(targetShiftId) ? "selected" : "";
                    const statusTag = isOpen ? "(Đang mở)" : "(Đã đóng)";
                    return `<option value="${s.id}" ${isSelected}>Ca ${s.id}: ${escapePosHtml(s.name)} ${statusTag}</option>`;
                })
                .join("");
            if (targetShiftId && targetShiftId !== "ALL") {
                selectEl.value = String(targetShiftId);
            }
        }
    }

    if (filterShiftEl) {
        if (shifts.length === 0) {
            filterShiftEl.innerHTML = '<option value="ALL">Tất cả ca bán hàng</option>';
        } else {
            let html = `<option value="ALL" ${targetShiftId === "ALL" ? "selected" : ""}>Tất cả ca bán hàng</option>`;
            shifts.forEach((s) => {
                const isOpen = String(s.status).toUpperCase() === "OPEN";
                const statusLabel = isOpen ? "(Đang mở)" : "(Đã đóng)";
                const isSelected = String(s.id) === String(targetShiftId) ? "selected" : "";
                html += `<option value="${s.id}" ${isSelected}>Ca ${s.id}: ${escapePosHtml(s.name)} ${statusLabel}</option>`;
            });
            filterShiftEl.innerHTML = html;
            if (targetShiftId) {
                filterShiftEl.value = String(targetShiftId);
            }
        }
    }

    updatePosShiftLockState();

    if (posOrdersCache && posOrdersCache.length > 0) {
        renderPosOrdersTable(posOrdersCache);
    }
}"""

assert old_load_shifts in pos_js, "old_load_shifts not found"
pos_js = pos_js.replace(old_load_shifts, new_load_shifts, 1)

with open("frontend/js/pos.js", "w", encoding="utf-8") as f:
    f.write(pos_js)

print("Updated frontend/js/pos.js successfully")
