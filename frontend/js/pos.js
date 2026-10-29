
function formatTimeOnly(dateStr) {
    if (!dateStr) return "--:--";
    const d = new Date(dateStr);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
// ==========================================================================
// QUẦY THU NGÂN & PHÁT HÀNH MÃ VIETQR ĐỘNG (frontend/js/pos.js)
// ==========================================================================

let posOrdersCache = [];
let currentSelectedOrderForQr = null;
let posPollingTimer = null;
let isCreatingOrder = false;
let isInitialOrderLoad = true;

// 1. Khởi tạo màn hình Quầy thu ngân
async function initPosPage() {
    bindPosEvents();
    initPosEventSource();
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
}

// 2. Gắn sự kiện cho các nút bấm trên giao diện
function bindPosEvents() {
    document.querySelectorAll(".quick-amount-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const amountInput = document.getElementById("pos-total-amount");
            if (amountInput) {
                amountInput.value = btn.getAttribute("data-amount") || "200000";
            }
        });
    });

    const createForm = document.getElementById("pos-create-order-form");
    if (createForm) {
        createForm.addEventListener("submit", handleCreatePosOrder);
    }

    const refreshBtn = document.getElementById("btn-pos-refresh");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => loadPosOrders(true));
    }

    const formShiftSelect = document.getElementById("pos-shift-select");
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
    }

    const filterSelect = document.getElementById("pos-filter-payment");
    if (filterSelect) {
        filterSelect.addEventListener("change", () => renderPosOrdersTable(posOrdersCache));
    }

    const searchInput = document.getElementById("pos-search-order");
    if (searchInput) {
        searchInput.addEventListener("input", () => renderPosOrdersTable(posOrdersCache));
    }

    const reissueBtn = document.getElementById("btn-reissue-qr");
    if (reissueBtn) {
        reissueBtn.addEventListener("click", () => {
            if (currentSelectedOrderForQr) {
                issueDynamicVietQr(currentSelectedOrderForQr.id, true);
            }
        });
    }

    const ttsToggle = document.getElementById("tts-enable-toggle");
    if (ttsToggle) {
        const saved = localStorage.getItem("recon_tts_enabled");
        if (saved !== null) ttsToggle.checked = saved !== "false";

        const updateTtsUi = (enabled) => {
            const timeEl = document.getElementById("tts-last-time");
            const msgEl = document.getElementById("tts-last-message");
            if (timeEl && (!msgEl?.dataset?.hasSpoken)) {
                timeEl.textContent = enabled ? "Đang bật" : "Đã tắt";
            }
            if (!enabled && msgEl && (!msgEl?.dataset?.hasSpoken)) {
                msgEl.textContent = "Loa đã tắt. Hệ thống vẫn ghi nhận thanh toán bình thường.";
            } else if (enabled && msgEl && (!msgEl?.dataset?.hasSpoken)) {
                msgEl.textContent = "Loa đang hoạt động. Sẽ tự động đọc thông báo khi nhận tiền thành công.";
            }
        };
        updateTtsUi(ttsToggle.checked);

        ttsToggle.addEventListener("change", (e) => {
            localStorage.setItem("recon_tts_enabled", String(e.target.checked));
            updateTtsUi(e.target.checked);
            showToast(e.target.checked ? "Đã bật loa báo nhận tiền." : "Đã tắt loa báo nhận tiền.", "info");
        });
    }

    // Tự động kiểm tra cập nhật ngay khi người dùng chuyển lại tab Quầy thu ngân
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            loadPosOrders(false, true);
        }
    });
}

let posShiftsCache = [];
let isCurrentShiftLocked = false;

// Cập nhật trạng thái khóa/mở giao diện tạo hóa đơn theo trạng thái và thời gian ca
function updatePosShiftLockState() {
    const selectEl = document.getElementById("pos-shift-select");
    const badgeEl = document.getElementById("pos-shift-status-badge");
    const alertBox = document.getElementById("pos-shift-closed-alert");
    const alertText = document.getElementById("pos-shift-closed-alert-text");
    const submitBtn = document.getElementById("btn-submit-order");
    const amountInput = document.getElementById("pos-total-amount");
    const noteInput = document.getElementById("pos-customer-note");
    const codeInput = document.getElementById("pos-order-code");
    const quickBtns = document.querySelectorAll(".quick-amount-btn");

    if (!selectEl) return;

    const selectedId = Number(selectEl.value || 0);
    const shift = posShiftsCache.find((s) => Number(s.id) === selectedId);

    const now = new Date();
    let isLocked = false;
    let lockReason = "";
    let badgeText = "Ca đang mở";
    let badgeClass = "fp-badge fp-badge-success";

    if (!shift) {
        isLocked = true;
        lockReason = "Không tìm thấy thông tin ca làm việc hoặc chưa có ca nào được mở.";
        badgeText = "Chưa có ca";
        badgeClass = "fp-badge fp-badge-warning";
    } else {
        const isClosed = String(shift.status).toUpperCase() === "CLOSED";
        const isDraft = String(shift.status).toUpperCase() === "DRAFT";
        const isCancelled = String(shift.status).toUpperCase() === "CANCELLED";
        const isExpired = shift.end_time && new Date(shift.end_time) <= now;
        const notStarted = shift.start_time && new Date(shift.start_time) > now;

        if (isClosed) {
            isLocked = true;
            lockReason = `Ca làm việc '${escapePosHtml(shift.name)}' đã kết thúc (ĐÃ ĐÓNG). Vui lòng mở ca mới để tiếp tục tạo đơn hàng.`;
            badgeText = "Ca đã đóng";
            badgeClass = "fp-badge fp-badge-danger";
        } else if (isExpired) {
            isLocked = true;
            lockReason = `Ca làm việc '${escapePosHtml(shift.name)}' đã hết thời gian hoạt động (kết thúc lúc ${formatDateTime(shift.end_time)}). Vui lòng mở ca mới để tiếp tục tạo đơn hàng.`;
            badgeText = "Hết giờ làm việc";
            badgeClass = "fp-badge fp-badge-danger";
        } else if (notStarted) {
            isLocked = true;
            lockReason = `Ca làm việc '${escapePosHtml(shift.name)}' chưa đến giờ bắt đầu (bắt đầu lúc ${formatDateTime(shift.start_time)}).`;
            badgeText = "Chưa bắt đầu";
            badgeClass = "fp-badge fp-badge-warning";
        } else if (isDraft || isCancelled) {
            isLocked = true;
            lockReason = `Ca làm việc đang ở trạng thái ${shift.status}, không thể nhận đơn hàng.`;
            badgeText = shift.status;
            badgeClass = "fp-badge fp-badge-neutral";
        }
    }

    isCurrentShiftLocked = isLocked;

    if (badgeEl) {
        if (!isLocked) {
            badgeEl.className = "shift-status-pill is-open";
            badgeEl.textContent = "● Ca đang hoạt động";
        } else {
            badgeEl.className = "shift-status-pill is-closed";
            badgeEl.textContent = "● " + badgeText;
        }
    }

    const headerShiftName = document.getElementById("pos-header-shift-name");
    if (headerShiftName) {
        if (shift) {
            const shiftCode = `CA-${String(shift.id).padStart(4, "0")}`;
            headerShiftName.textContent = `${shift.name} • ${shiftCode}`;
        } else {
            headerShiftName.textContent = "Tất cả ca bán hàng";
        }
    }

    if (alertBox) {
        if (isLocked) {
            alertBox.classList.remove("d-none");
            if (alertText) alertText.innerHTML = `<strong>Không thể tạo đơn:</strong> ${lockReason}`;
        } else {
            alertBox.classList.add("d-none");
        }
    }

    if (submitBtn) {
        submitBtn.disabled = isLocked;
        if (isLocked) {
            submitBtn.classList.add("disabled");
            submitBtn.title = lockReason;
        } else {
            submitBtn.classList.remove("disabled");
            submitBtn.title = "Tạo đơn hàng & Xuất mã QR thanh toán";
        }
    }

    if (amountInput) amountInput.disabled = isLocked;
    if (noteInput) noteInput.disabled = isLocked;
    if (codeInput) codeInput.disabled = isLocked;
    quickBtns.forEach((btn) => (btn.disabled = isLocked));
}

// 3. Tải danh sách ca đang mở bán và đồng bộ chính xác ca được chỉ định từ URL
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
}

// 4. Tải danh sách hóa đơn và kiểm tra phát loa thông báo
// 4. Tải danh sách hóa đơn và kiểm tra phát loa thông báo
async function loadPosOrders(isManualRefresh = false, isFromPolling = false) {
    try {
        const ordersRes = await apiRequest("/orders");
        posOrdersCache = Array.isArray(ordersRes) ? ordersRes : (ordersRes.items || ordersRes.orders || []);
    } catch (_) {
        const store = getDemoStore();
        posOrdersCache = store.orders || [];
    }

    // Kiểm tra nếu vừa từ trang Cổng thanh toán tự động quay về sau khi chuyển khoản
    const justPaidCode = sessionStorage.getItem("recon_just_paid_order");
    if (justPaidCode) {
        sessionStorage.removeItem("recon_just_paid_order");
    }

    if (typeof announceOrderChangeIfNeeded === "function") {
        posOrdersCache.forEach((ord) => {
            const isJustPaid = justPaidCode && String(ord.order_code).toUpperCase() === String(justPaidCode).toUpperCase();
            announceOrderChangeIfNeeded(ord, {
                isInitialSnapshot: isInitialOrderLoad && !isJustPaid
            });
        });
    }
    isInitialOrderLoad = false;

    renderPosOrdersTable(posOrdersCache);

    if (currentSelectedOrderForQr) {
        const updated = posOrdersCache.find((o) => Number(o.id) === Number(currentSelectedOrderForQr.id));
        if (updated) {
            const wasPaidBefore = String(currentSelectedOrderForQr.payment_status).toUpperCase() === "PAID";
            const isPaidNow = String(updated.payment_status).toUpperCase() === "PAID";
            currentSelectedOrderForQr = updated;
            const modalEl = document.getElementById("vietqrModal");
            if (isPaidNow && !wasPaidBefore && modalEl && modalEl.classList.contains("show")) {
                displayQrInModal(updated, updated.qr_request || updated.active_qr);
            }
        }
    }

    if (isManualRefresh && !isFromPolling) {
        showToast("Đã làm mới danh sách hóa đơn.", "success");
    }
}

// ==========================================================================
// KIẾN TRÚC THỜI GIAN THỰC: SERVER-SENT EVENTS (SSE) & PHÁT LOA TỨC THỜI (< 100ms)
// ==========================================================================
let posEventSource = null;

function initPosEventSource() {
    if (posEventSource) {
        try { posEventSource.close(); } catch (_) {}
    }

    try {
        const streamUrl = `${API_BASE_URL}/events/stream`;
        posEventSource = new EventSource(streamUrl);

        posEventSource.onopen = () => {
            console.log("SSE Real-time Stream connected to /events/stream");
            updateSseStatusBadge(true);
        };

        posEventSource.addEventListener("order_updated", (event) => {
            try {
                const updatedOrder = JSON.parse(event.data);
                handleOrderUpdateEvent(updatedOrder);
            } catch (err) {
                console.error("Error processing SSE order_updated:", err);
            }
        });

        posEventSource.addEventListener("payment_received", (event) => {
            try {
                const payment = JSON.parse(event.data);
                if (typeof showToast === "function") {
                    const amtStr = new Intl.NumberFormat('vi-VN').format(payment.amount);
                    showToast(`TingTing: Nhận +${amtStr} ₫ (GD: ${payment.reference_code})`, "info");
                }
            } catch (err) {
                console.error("Error processing SSE payment_received:", err);
            }
        });

        posEventSource.onerror = (err) => {
            console.warn("SSE connection interrupted, browser auto-reconnecting...", err);
            updateSseStatusBadge(false);
        };
    } catch (e) {
        console.warn("EventSource failed to initialize:", e);
    }
}

function updateSseStatusBadge(isConnected) {
    const badge = document.getElementById("pos-sse-status-badge");
    if (badge) {
        if (isConnected) {
            badge.className = "shift-status-pill is-open";
            badge.innerHTML = "● Đang cập nhật";
        } else {
            badge.className = "shift-status-pill is-closed";
            badge.innerHTML = "● Đang kết nối lại";
        }
    }
}

function handleOrderUpdateEvent(updatedOrder) {
    if (!updatedOrder || !updatedOrder.id) return;

    // 1. Cập nhật cache đơn hàng trong bộ nhớ POS
    const idx = posOrdersCache.findIndex((o) => Number(o.id) === Number(updatedOrder.id));
    if (idx >= 0) {
        posOrdersCache[idx] = updatedOrder;
    } else {
        posOrdersCache.unshift(updatedOrder);
    }

    // 2. Tự động phát loa thông báo ngay lập tức (< 100ms) qua Web Speech API
    if (typeof announceOrderChangeIfNeeded === "function") {
        announceOrderChangeIfNeeded(updatedOrder, { isInitialSnapshot: false });
    }

    // 3. Render lại bảng danh sách hóa đơn
    renderPosOrdersTable(posOrdersCache);

    // 4. Nếu đang mở modal VietQR của đơn này -> Cập nhật trạng thái hiển thị
    if (currentSelectedOrderForQr && Number(currentSelectedOrderForQr.id) === Number(updatedOrder.id)) {
        currentSelectedOrderForQr = updatedOrder;
        const modalEl = document.getElementById("vietqrModal");
        if (modalEl && modalEl.classList.contains("show")) {
            displayQrInModal(updatedOrder, updatedOrder.qr_request || updatedOrder.active_qr);
        }
    }
}

// 5. Tự động đồng bộ dự phòng (Fallback Polling mỗi 20 giây thay vì 2 giây, giảm 90% tải DB)
let shiftCheckTick = 0;
function startPosPolling() {
    if (posPollingTimer) clearInterval(posPollingTimer);
    posPollingTimer = setInterval(async () => {
        if (document.hidden) return;
        shiftCheckTick++;
        try {
            const data = await apiRequest("/shifts");
            posShiftsCache = Array.isArray(data) ? data : (data.items || data.shifts || []);
            updatePosShiftLockState();
        } catch (_) {}
    }, 20000);
}

// 6. Hiển thị bảng danh sách hóa đơn và đồng bộ số liệu đối soát sổ quỹ
function renderPosOrdersTable(orders) {
    const tbody = document.getElementById("pos-orders-tbody");
    if (!tbody) return;

    const shiftFilterVal = document.getElementById("pos-shift-select")?.value || document.getElementById("pos-filter-shift")?.value || "ALL";
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
                <td colspan="6" class="text-center py-4 text-secondary">
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

            const isPartial = !isPaid && paid > 0;

            return `
                <tr class="${isCancelled ? "table-light text-muted" : ""}">
                    <td>
                        <div class="fw-bold ${isCancelled ? "text-muted text-decoration-line-through" : "text-dark"} font-numeric" style="font-size: 0.94rem;">
                            ${escapePosHtml(ord.order_code)}
                        </div>
                        ${ord.note ? `<div class="text-secondary small mt-0.5" style="font-size: 0.75rem;">${escapePosHtml(ord.note)}</div>` : ""}
                    </td>
                    <td>
                        <span class="text-secondary font-numeric" style="font-size: 0.86rem;">
                            ${formatTimeOnly(ord.created_at)}
                        </span>
                    </td>
                    <td>
                        <span class="fw-bold font-numeric ${isCancelled ? "text-muted text-decoration-line-through" : "text-dark"}">
                            ${formatVND(total)}
                        </span>
                    </td>
                    <td>
                        ${
                            isCancelled
                                ? `<span class="text-muted font-numeric">0 ₫</span>`
                                : isPaid
                                ? `<span class="fw-bold text-dark font-numeric">${formatVND(total)}</span>`
                                : isPartial
                                ? `<div>
                                       <span class="fw-bold text-dark font-numeric">${formatVND(paid)}</span>
                                       <div class="text-warning small font-numeric" style="font-size: 0.74rem;">Còn ${formatVND(remaining)}</div>
                                   </div>`
                                : `<span class="text-secondary font-numeric">0 ₫</span>`
                        }
                    </td>
                    <td>
                        ${
                            isCancelled
                                ? `<span class="pos-status-pill pos-status-cancelled">Đã hủy</span>`
                                : isPaid
                                ? `<span class="pos-status-pill pos-status-paid">Đã thu đủ</span>`
                                : isPartial
                                ? `<span class="pos-status-pill pos-status-partial">Thu một phần</span>`
                                : `<span class="pos-status-pill pos-status-unpaid">Chờ thanh toán</span>`
                        }
                    </td>
                    <td class="text-end">
                        ${
                            isCancelled
                                ? `<button type="button" class="btn btn-sm btn-light border text-muted py-1 px-2" disabled style="font-size: 0.75rem;">Đã hủy</button>`
                                : isPaid
                                ? `<button type="button" class="btn-pos-receipt" onclick="openOrderQrModal(${ord.id}, false)">
                                       <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                           <path stroke-linecap="round" stroke-linejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z"/>
                                       </svg>
                                       <span>Biên lai</span>
                                   </button>`
                                : `<button type="button" class="btn-pos-qr" onclick="openOrderQrModal(${ord.id}, true)">
                                       ${getHeroicon("qr-code", "hi-icon hi-icon-sm")}
                                       <span>Xuất QR</span>
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}

// 7. Tạo hóa đơn mới và bật mã QR ngay lập tức
async function handleCreatePosOrder(event) {
    event.preventDefault();
    if (isCreatingOrder) return;

    if (isCurrentShiftLocked) {
        showToast("Ca làm việc đã kết thúc hoặc không hợp lệ. Vui lòng mở ca mới để tiếp tục tạo đơn hàng.", "danger");
        return;
    }

    const shiftId = Number(document.getElementById("pos-shift-select")?.value || 1);
    const customCode = (document.getElementById("pos-order-code")?.value || "").trim().toUpperCase();
    const totalAmount = Number(document.getElementById("pos-total-amount")?.value || 0);
    const note = (document.getElementById("pos-customer-note")?.value || "").trim();
    const errorBox = document.getElementById("pos-create-order-error");
    const submitBtn = document.getElementById("btn-submit-order");

    if (errorBox) errorBox.classList.add("d-none");

    if (!Number.isFinite(totalAmount) || totalAmount <= 0) {
        if (errorBox) {
            errorBox.textContent = "Vui lòng nhập số tiền thanh toán lớn hơn 0 VNĐ.";
            errorBox.classList.remove("d-none");
        }
        return;
    }

    isCreatingOrder = true;
    const oldBtnHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Đang tạo đơn...`;
    }

    let targetOrderId = null;

    try {
        const createdOrder = await apiRequest("/orders", {
            method: "POST",
            body: JSON.stringify({
                shift_id: shiftId,
                order_code: customCode || undefined,
                total_amount: totalAmount,
                note: note || undefined
            })
        });
        targetOrderId = createdOrder.id;
        await loadPosOrders(false);
    } catch (error) {
        if (error.isNetworkError) {
            const store = getDemoStore();
            const nextNum = 1001 + (store.orders?.length || 4);
            const generatedCode = customCode || `ORD${nextNum}`;
            const newOrder = {
                id: Date.now(),
                shift_id: shiftId,
                order_code: generatedCode,
                note: note || "Khách mua tại quầy",
                total_amount: totalAmount,
                net_paid_amount: 0,
                overpaid_amount: 0,
                order_status: "CONFIRMED_ORDER",
                payment_status: "UNPAID",
                qr_request: null,
                created_at: new Date().toISOString()
            };
            store.orders.unshift(newOrder);
            saveDemoStore(store);
            posOrdersCache = store.orders;
            targetOrderId = newOrder.id;
            renderPosOrdersTable(posOrdersCache);
        } else {
            if (errorBox) {
                errorBox.textContent = error.message;
                errorBox.classList.remove("d-none");
            }
            isCreatingOrder = false;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = oldBtnHtml;
            }
            return;
        }
    }

    isCreatingOrder = false;
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = oldBtnHtml;
    }

    const codeInput = document.getElementById("pos-order-code");
    const noteInput = document.getElementById("pos-customer-note");
    if (codeInput) codeInput.value = "";
    if (noteInput) noteInput.value = "";

    if (targetOrderId) {
        await issueDynamicVietQr(targetOrderId, false);
    }
}

// 8. Sinh đường dẫn ảnh mã VietQR chuẩn EMVCo và hiển thị hộp thoại
function buildEmvcoVietQrUrl(orderCode, expectedAmount) {
    const bankBin = "970422";
    const accountNo = "0888999777";
    const amount = Math.round(Number(expectedAmount || 0));
    const addInfo = encodeURIComponent(`TT ${orderCode}`);
    const accountName = encodeURIComponent("CTY TNHH RECONHUB RETAIL");
    return `https://img.vietqr.io/image/${bankBin}-${accountNo}-compact2.png?amount=${amount}&addInfo=${addInfo}&accountName=${accountName}`;
}

async function openOrderQrModal(orderId, shouldIssueIfMissing = true) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    currentSelectedOrderForQr = order;
    const isPaid = String(order.payment_status || "").toUpperCase() === "PAID";
    const totalAmount = Number(order.total_amount || 0);
    const paidAmount = Number(order.net_paid_amount ?? order.paid_amount ?? order.allocated_amount ?? 0);
    const remainingAmount = Math.max(0, totalAmount - paidAmount);

    const existingQr = order.qr_request || order.active_payment_request || order.active_qr;
    const qrAmountMismatch = existingQr && Math.round(Number(existingQr.expected_amount || 0)) !== Math.round(remainingAmount);

    // Nếu đơn hàng chưa thanh toán đủ và chưa có QR hoặc mã QR cũ không khớp với số tiền còn thiếu
    if (!isPaid && shouldIssueIfMissing && (!existingQr || existingQr.status !== "ACTIVE" || qrAmountMismatch)) {
        await issueDynamicVietQr(order.id, false);
    } else {
        displayQrInModal(order, existingQr);
    }
}

async function issueDynamicVietQr(orderId, isReissue = false) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    const paidAmount = Number(order.net_paid_amount ?? order.paid_amount ?? order.allocated_amount ?? 0);
    const remainingAmount = Math.max(0, Number(order.total_amount || 0) - paidAmount);
    const expected = remainingAmount > 0 ? remainingAmount : Number(order.total_amount || 0);

    try {
        const qrResp = await apiRequest("/payment-requests", {
            method: "POST",
            body: JSON.stringify({
                order_id: orderId,
                expected_amount: expected
            })
        });
        await loadPosOrders(false);
        const updatedOrder = posOrdersCache.find((o) => Number(o.id) === Number(orderId)) || order;
        displayQrInModal(updatedOrder, qrResp);
    } catch (error) {
        if (error.isNetworkError) {
            const store = getDemoStore();
            const target = store.orders.find((o) => Number(o.id) === Number(orderId));
            const simulatedQr = {
                request_code: `REQ-${order.order_code}-${Math.floor(10 + Math.random() * 89)}`,
                expected_amount: expected,
                status: "ACTIVE",
                qr_url: buildEmvcoVietQrUrl(order.order_code, expected),
                expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString()
            };
            if (target) {
                target.qr_request = simulatedQr;
                saveDemoStore(store);
                posOrdersCache = store.orders;
            }
            order.qr_request = simulatedQr;
            renderPosOrdersTable(posOrdersCache);
            displayQrInModal(order, simulatedQr);
        } else {
            showToast(error.message || "Không thể xuất mã QR.", "danger");
            return;
        }
    }

    showToast(
        isReissue ? `Đã đổi mã QR mới cho đơn ${order.order_code}` : `Đã tạo mã QR cho đơn ${order.order_code}`,
        "success"
    );
}

function displayQrInModal(order, qrData) {
    if (!order) return;
    currentSelectedOrderForQr = order;

    const isPaid = String(order.payment_status || "").toUpperCase() === "PAID";
    const totalAmount = Number(order.total_amount || 0);
    const paidAmount = Number(order.net_paid_amount ?? order.paid_amount ?? order.allocated_amount ?? 0);
    const remainingAmount = Math.max(0, totalAmount - paidAmount);
    const isPartial = String(order.payment_status || "").toUpperCase() === "PARTIALLY_PAID" || (!isPaid && paidAmount > 0 && remainingAmount > 0);

    // Xác định số tiền hiển thị trên QR: Với đơn chuyển thiếu, BẮT BUỘC là số tiền còn thiếu
    let expectedAmount;
    if (isPaid) {
        expectedAmount = paidAmount > 0 ? paidAmount : totalAmount;
    } else if (isPartial) {
        expectedAmount = remainingAmount;
    } else {
        expectedAmount = Math.round(Number(qrData?.expected_amount || remainingAmount || totalAmount));
    }

    // Nếu đơn hàng chưa thanh toán đủ hoặc chuyển thiếu, bảo đảm URL mã QR chứa đúng số tiền còn thiếu
    let qrUrl = qrData?.qr_url;
    if (!isPaid) {
        if (!qrUrl || isPartial || Math.round(Number(qrData?.expected_amount || 0)) !== expectedAmount) {
            qrUrl = buildEmvcoVietQrUrl(order.order_code, expectedAmount);
        }
    }

    const badgeEl = document.getElementById("modal-qr-status-badge");
    const titleEl = document.getElementById("modal-qr-title");
    const qrFrameBox = document.getElementById("modal-qr-frame-box");
    const actionsEl = document.getElementById("modal-qr-actions");
    const paidTimeRow = document.getElementById("modal-qr-paid-time-row");
    const paidTimeEl = document.getElementById("modal-qr-paid-time");

    if (badgeEl) {
        if (isPaid) {
            badgeEl.className = "fp-badge fp-badge-success mb-1";
            badgeEl.textContent = "✓ Đã thanh toán đủ";
        } else if (isPartial) {
            badgeEl.className = "fp-badge fp-badge-warning mb-1";
            badgeEl.textContent = "● Khách chuyển thiếu - Cần thu tiếp";
        } else {
            badgeEl.className = "fp-badge fp-badge-dark mb-1";
            badgeEl.textContent = "Mã QR đang hoạt động";
        }
    }

    if (titleEl) {
        if (isPaid) {
            titleEl.textContent = "Biên Lai Thanh Toán";
        } else if (isPartial) {
            titleEl.textContent = "Mã QR Thu Tiếp Số Tiền Còn Thiếu";
        } else {
            titleEl.textContent = "Quét Mã VietQR Thanh Toán";
        }
    }

    // Nếu đã thanh toán (Xem biên lai): Ẩn ảnh QR và ẩn 2 nút hành động, chỉ hiện các dòng thông tin biên lai
    if (qrFrameBox) {
        qrFrameBox.classList.toggle("d-none", isPaid);
    }
    if (actionsEl) {
        actionsEl.classList.toggle("d-none", isPaid);
    }
    if (paidTimeRow) {
        paidTimeRow.classList.toggle("d-none", !isPaid);
    }

    if (paidTimeEl && isPaid) {
        const txTime =
            order.paid_at ||
            order.last_payment_at ||
            qrData?.created_at ||
            order.created_at;
        paidTimeEl.textContent = formatDateTime(txTime);
    }

    const imgEl = document.getElementById("modal-qr-image");
    const ordCodeEl = document.getElementById("modal-qr-order-code");
    const amountEl = document.getElementById("modal-qr-expected-amount");
    const contentEl = document.getElementById("modal-qr-transfer-content");
    const simLinkEl = document.getElementById("modal-link-simulator");

    const totalRow = document.getElementById("modal-qr-total-row");
    const totalEl = document.getElementById("modal-qr-total-amount");
    const paidRow = document.getElementById("modal-qr-paid-amount-row");
    const paidEl = document.getElementById("modal-qr-paid-amount");
    const amountLabel = document.getElementById("modal-qr-amount-label");

    if (totalRow) totalRow.classList.toggle("d-none", !isPartial);
    if (paidRow) paidRow.classList.toggle("d-none", !isPartial);
    if (totalEl) totalEl.textContent = formatVND(totalAmount);
    if (paidEl) paidEl.textContent = formatVND(paidAmount);

    if (amountLabel) {
        if (isPaid) {
            amountLabel.textContent = "Số tiền đã thu:";
        } else if (isPartial) {
            amountLabel.textContent = "Số tiền còn thiếu:";
        } else {
            amountLabel.textContent = "Số tiền:";
        }
    }

    if (imgEl && !isPaid) imgEl.src = qrUrl;
    if (ordCodeEl) ordCodeEl.textContent = order.order_code;
    if (amountEl) {
        amountEl.textContent = formatVND(expectedAmount);
        if (isPartial) {
            amountEl.className = "text-danger fw-bold fs-5 font-numeric";
        } else {
            amountEl.className = "text-primary fw-bold fs-6 font-numeric";
        }
    }
    if (contentEl) {
        contentEl.textContent = order.last_transfer_content || `TT ${order.order_code}`;
    }

    if (simLinkEl) {
        const currentShift = document.getElementById("pos-shift-select")?.value || document.getElementById("pos-filter-shift")?.value || order.shift_id || "";
        const returnUrl =
            currentShift && currentShift !== "ALL"
                ? `pos.html?shift_id=${encodeURIComponent(currentShift)}`
                : "pos.html";
        simLinkEl.href = `bank-simulator.html?order_code=${encodeURIComponent(order.order_code)}&amount=${encodeURIComponent(expectedAmount)}&return_url=${encodeURIComponent(returnUrl)}`;
        simLinkEl.textContent = isPartial ? "Thu tiếp đơn này →" : "Thanh toán đơn này →";
    }

    const modalEl = document.getElementById("vietqrModal");
    if (modalEl) {
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
}

function escapePosHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}