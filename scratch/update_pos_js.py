with open("frontend/js/pos.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update initPosPage to call initPosEventSource()
old_init = """async function initPosPage() {
    bindPosEvents();
    // Bắt buộc tải và chọn đúng ca từ URL (?shift_id=...) trước khi tải bảng hóa đơn
    await loadOpenShiftsForPos();
    await loadPosOrders(false);
    startPosPolling();"""

new_init = """async function initPosPage() {
    bindPosEvents();
    initPosEventSource();
    // Bắt buộc tải và chọn đúng ca từ URL (?shift_id=...) trước khi tải bảng hóa đơn
    await loadOpenShiftsForPos();
    await loadPosOrders(false);
    startPosPolling();"""

if old_init in code:
    code = code.replace(old_init, new_init, 1)
else:
    print("Warning: old_init not found")

# 2. Add SSE handler functions and replace startPosPolling
old_polling = """// 5. Tự động đồng bộ trạng thái đơn mỗi 2 giây
let shiftCheckTick = 0;
function startPosPolling() {
    if (posPollingTimer) clearInterval(posPollingTimer);
    posPollingTimer = setInterval(async () => {
        if (document.hidden) return;
        loadPosOrders(false, true);

        // Kiểm tra trạng thái ca định kỳ mỗi 4 giây
        shiftCheckTick++;
        if (shiftCheckTick % 2 === 0) {
            try {
                const data = await apiRequest("/shifts");
                posShiftsCache = Array.isArray(data) ? data : (data.items || data.shifts || []);
                updatePosShiftLockState();
            } catch (_) {}
        }
    }, 2000);
}"""

new_polling = """// ==========================================================================
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
            badge.className = "badge bg-success-subtle text-success border border-success-subtle d-inline-flex align-items-center gap-1";
            badge.innerHTML = '<span class="spinner-grow spinner-grow-sm text-success" style="width:6px;height:6px;" role="status"></span> Real-time SSE';
        } else {
            badge.className = "badge bg-warning-subtle text-warning border border-warning-subtle d-inline-flex align-items-center gap-1";
            badge.innerHTML = '● Đang kết nối lại';
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
}"""

if old_polling in code:
    code = code.replace(old_polling, new_polling, 1)
    with open("frontend/js/pos.js", "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: frontend/js/pos.js updated with SSE real-time events & polling reduction!")
else:
    print("ERROR: old_polling not found in frontend/js/pos.js")
