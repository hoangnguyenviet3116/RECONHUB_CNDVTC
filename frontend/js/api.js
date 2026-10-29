// ==========================================================================
// VIETQR RECONHUB — KẾT NỐI API & TIỆN ÍCH HỆ THỐNG DÙNG CHUNG
// ==========================================================================

const API_BASE_URL = "http://localhost:8000";
const DEMO_STORE_KEY = "reconhub_live_store_v4";

// Khởi tạo trạng thái rỗng chuẩn: Dữ liệu chỉ hình thành từ hoạt động thực tế trên Web
function getInitialDemoStore() {
    return {
        shifts: [],
        orders: [],
        bank_transactions: [],
        allocations: [],
        decisions: []
    };
}

function getDemoStore() {
    try {
        const raw = localStorage.getItem(DEMO_STORE_KEY);
        if (!raw) {
            const init = getInitialDemoStore();
            localStorage.setItem(DEMO_STORE_KEY, JSON.stringify(init));
            return init;
        }
        return JSON.parse(raw);
    } catch (_) {
        return getInitialDemoStore();
    }
}

function saveDemoStore(store) {
    try {
        localStorage.setItem(DEMO_STORE_KEY, JSON.stringify(store));
    } catch (_) {}
}

function resetDemoStore() {
    localStorage.removeItem(DEMO_STORE_KEY);
    showToast("Đã làm mới dữ liệu bộ nhớ đệm trình duyệt.", "info");
    setTimeout(() => window.location.reload(), 350);
}

function computeStoreSummary(store, shiftId = null) {
    const allOrders = store.orders || [];
    const scopedOrders = (shiftId && String(shiftId).toUpperCase() !== "ALL")
        ? allOrders.filter(o => String(o.shift_id) === String(shiftId))
        : allOrders;

    const validOrders = scopedOrders.filter((o) =>
        ["CONFIRMED_ORDER", "UNDER_REVIEW"].includes(String(o.order_status).toUpperCase())
    );
    const cancelledOrders = scopedOrders.filter((o) =>
        String(o.order_status).toUpperCase() === "CANCELLED_ORDER"
    );

    const validOrderTotal = validOrders.reduce((s, o) => s + Number(o.total_amount || 0), 0);
    const cancelledOrderTotal = cancelledOrders.reduce((s, o) => s + Number(o.total_amount || 0), 0);
    const totalOrderAmount = scopedOrders.reduce((s, o) => s + Number(o.total_amount || 0), 0);

    const activeQrTotal = validOrders.reduce((s, o) => {
        const qr = o.qr_request;
        if (qr && ["ACTIVE", "FULFILLED"].includes(String(qr.status).toUpperCase())) {
            return s + Number(qr.expected_amount || o.total_amount || 0);
        }
        return s;
    }, 0);

   const scopedOrderIds = new Set(scopedOrders.map((o) => Number(o.id)));
    const scopedOrderCodes = new Set(scopedOrders.map((o) => String(o.order_code)));
    const scopedAllocations =
        shiftId && String(shiftId).toUpperCase() !== "ALL"
            ? (store.allocations || []).filter(
                  (a) => scopedOrderIds.has(Number(a.order_id)) || scopedOrderCodes.has(String(a.order_code))
              )
            : store.allocations || [];

    const netAllocated = scopedAllocations.reduce((s, a) => s + Number(a.allocated_amount || 0), 0);
    const unallocatedBank = (store.bank_transactions || [])
        .filter((t) => ["UNMATCHED", "PARTIALLY_ALLOCATED"].includes(String(t.match_status).toUpperCase()))
        .reduce((s, t) => s + Number(t.unallocated_amount || 0), 0);

    const shifts = store.shifts || [];
    let targetRev = 0;
    if (shiftId && String(shiftId).toUpperCase() !== "ALL") {
        const matchedShift = shifts.find(s => String(s.id) === String(shiftId));
        if (matchedShift) targetRev = Number(matchedShift.target_revenue || 0);
    } else {
        targetRev = shifts.reduce((s, sh) => s + Number(sh.target_revenue || 0), 0);
    }

    return {
        shift_id: shiftId || (shifts.length > 0 ? String(shifts[0].id) : "NONE"),
        shift_name: shiftId === "ALL" ? "Tất cả ca bán hàng" : (shifts.length > 0 ? `Ca ${shiftId || shifts[0].id}` : "Chưa có ca làm việc"),
        target_revenue: targetRev,
        valid_order_total: validOrderTotal,
        cancelled_order_total: cancelledOrderTotal,
        total_order_amount: totalOrderAmount,
        total_order_count: scopedOrders.length,
        valid_order_count: validOrders.length,
        cancelled_order_count: cancelledOrders.length,
        active_qr_request_total: activeQrTotal,
        allocated_payment_total: netAllocated,
        unissued_qr_amount: Math.max(0, validOrderTotal - activeQrTotal),
        pending_qr_collection: Math.max(0, activeQrTotal - netAllocated),
        remaining_receivable: Math.max(0, validOrderTotal - netAllocated),
        unallocated_bank_tx_total: unallocatedBank,
        total_bank_received: netAllocated + unallocatedBank,
        ledger_integrity_valid: true,
        orders: scopedOrders,
        available_shifts: shifts,
        ledger_entries: store.allocations || [],
        bank_transactions: store.bank_transactions || [],
        payment_allocations: store.allocations || [],
        decisions: store.decisions || []
    };
}

function getCurrentRole() {
    return localStorage.getItem("recon_role") || "OWNER";
}

function getCurrentMerchantId() {
    return Number(localStorage.getItem("recon_merchant_id") || "1");
}

function getCurrentUserId() {
    const role = getCurrentRole();
    if (role === "CASHIER") return 2;
    if (role === "REVIEWER") return 3;
    return 1;
}

function setCurrentRole(role) {
    localStorage.setItem("recon_role", role);
    const roleNames = {
        CASHIER: "Thu ngân",
        REVIEWER: "Kế toán",
        OWNER: "Chủ cửa hàng"
    };
    showToast(`Đã chuyển tài khoản: ${roleNames[role] || role}`, "info");
    setTimeout(() => window.location.reload(), 300);
}

async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
    const defaultHeaders = {
        "Content-Type": "application/json",
        "X-Demo-Role": getCurrentRole(),
        "X-Merchant-Id": String(getCurrentMerchantId()),
        "X-User-Id": String(getCurrentUserId())
    };

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    };

    try {
        const response = await fetch(url, config);
        const contentType = response.headers.get("content-type") || "";
        const payload = contentType.includes("application/json")
            ? await response.json().catch(() => ({}))
            : await response.text().catch(() => "");

        if (!response.ok) {
            const detail =
                (payload && typeof payload === "object" && (payload.detail || payload.message)) ||
                `Không thể thực hiện yêu cầu (${response.status})`;
            const error = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
            error.status = response.status;
            error.payload = payload;
            throw error;
        }
        return payload;
    } catch (err) {
        if (err.name === "TypeError" || String(err.message).includes("Failed to fetch")) {
            const netErr = new Error("Offline Store Mode");
            netErr.isNetworkError = true;
            throw netErr;
        }
        throw err;
    }
}

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatVND(amount) {
    const value = Number(amount || 0);
    return new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0
    }).format(value);
}

function formatNumber(amount) {
    return new Intl.NumberFormat("vi-VN").format(Number(amount || 0));
}

function formatDateTime(isoString) {
    if (!isoString) return "—";
    const s = String(isoString).replace(" ", "T");
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return String(isoString);
    return d.toLocaleString("vi-VN", {
        hour12: false,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}

const HEROICONS_PATHS = {
    "calendar": `<path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />`,    "computer-desktop": `<path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0H3" />`,
    "building-library": `<path stroke-linecap="round" stroke-linejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z" />`,
    "arrows-right-left": `<path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />`,
    "chart-bar": `<path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />`,
    "lock-closed": `<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />`,
    "banknotes": `<path d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"/>`,
    "qr-code": `<path d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0 1 3.75 9.375v-4.5ZM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 0 1-1.125-1.125v-4.5ZM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0 1 13.5 9.375v-4.5Z"/><path d="M6.75 6.75h.75v.75h-.75v-.75ZM6.75 16.5h.75v.75h-.75v-.75ZM16.5 6.75h.75v.75h-.75v-.75ZM13.5 13.5h.75v.75h-.75v-.75ZM13.5 19.5h.75v.75h-.75v-.75ZM19.5 13.5h.75v.75h-.75v-.75ZM19.5 19.5h.75v.75h-.75v-.75ZM16.5 16.5h.75v.75h-.75v-.75Z"/>`,
    "shield-check": `<path d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"/>`,
    "arrow-up-right": `<path d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25"/>`,
    "arrow-right": `<path d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"/>`,
    "arrow-path": `<path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"/>`,
    "clock": `<path d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>`,
    "check-circle": `<path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>`,
    "exclamation-triangle": `<path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"/>`,
    "speaker-wave": `<path d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"/>`,
    "finger-print": `<path d="M7.864 4.243A7.5 7.5 0 0 1 19.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 0 0 4.5 10.5a7.464 7.464 0 0 1-1.15 3.993m1.989 3.559A11.209 11.209 0 0 0 8.25 10.5a3.75 3.75 0 1 1 7.5 0c0 .527-.021 1.049-.064 1.565M12 10.5a14.94 14.94 0 0 1-3.6 9.75m6.633-4.596a18.666 18.666 0 0 1-2.485 5.33"/>`,
    "plus": `<path d="M12 4.5v15m7.5-7.5h-15"/>`,
    "document-text": `<path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"/>`,
    "archive-box": `<path stroke-linecap="round" stroke-linejoin="round" d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />`,
    "sparkles": `<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>`,
    "chat-bubble": `<path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v5.518Z"/>`,
    "paper-airplane": `<path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"/>`
};

function getHeroicon(name, className = "hi-icon") {
    const path = HEROICONS_PATHS[name] || HEROICONS_PATHS["shield-check"];
    return `<svg class="${className}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${path}</svg>`;
}

function renderStatusBadge(status) {
    const s = String(status || "").toUpperCase();
    const map = {
        OPEN: { cls: "fp-badge-success", label: "Đang mở bán" },
        CLOSED: { cls: "fp-badge-neutral", label: "Đã đóng ca" },
        DRAFT: { cls: "fp-badge-neutral", label: "Bản nháp" },
        CANCELLED: { cls: "fp-badge-danger", label: "Đã hủy" },

        CONFIRMED_ORDER: { cls: "fp-badge-dark", label: "Đơn hợp lệ" },
        UNDER_REVIEW: { cls: "fp-badge-warning", label: "Đang rà soát" },
        CANCELLED_ORDER: { cls: "fp-badge-danger", label: "Đã hủy" },
        PAID: { cls: "fp-badge-success", label: "Đã thanh toán" },
        PARTIALLY_PAID: { cls: "fp-badge-warning", label: "Thanh toán 1 phần" },
        UNPAID: { cls: "fp-badge-neutral", label: "Chờ thanh toán" },

        ACTIVE: { cls: "fp-badge-dark", label: "QR đang hoạt động" },
        FULFILLED: { cls: "fp-badge-success", label: "QR hoàn tất" },
        REVOKED: { cls: "fp-badge-neutral", label: "QR đã hủy" },
        EXPIRED: { cls: "fp-badge-neutral", label: "QR hết hạn" },

        FULLY_ALLOCATED: { cls: "fp-badge-success", label: "Đã khớp đơn" },
        PARTIALLY_ALLOCATED: { cls: "fp-badge-warning", label: "Còn tiền dư" },
        UNMATCHED: { cls: "fp-badge-danger", label: "Chưa rõ đơn" },
        REJECTED_TX: { cls: "fp-badge-danger", label: "Từ chối" },
        ALLOCATION: { cls: "fp-badge-success", label: "Thu tiền đơn hàng" },
        REVERSAL: { cls: "fp-badge-danger", label: "Hoàn / Đảo bút toán" }
    };

    const item = map[s] || { cls: "fp-badge-neutral", label: s || "—" };
    return `<span class="fp-badge ${item.cls}">${item.label}</span>`;
}

function showToast(message, type = "success") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.setAttribute("role", "status");
        container.setAttribute("aria-live", "polite");
        document.body.appendChild(container);
    }

    const styles = {
        success: { border: "#059669", bg: "#ecfdf5", color: "#065f46", icon: "check-circle" },
        danger: { border: "#e11d48", bg: "#fff1f2", color: "#9f1239", icon: "exclamation-triangle" },
        warning: { border: "#d97706", bg: "#fffbeb", color: "#92400e", icon: "exclamation-triangle" },
        info: { border: "#2563eb", bg: "#eff6ff", color: "#1e40af", icon: "shield-check" }
    };

    const st = styles[type] || styles.info;
    const toast = document.createElement("div");
    toast.style.cssText = `
        background:${st.bg};
        color:${st.color};
        border:1.5px solid ${st.border};
        border-radius:12px;
        padding:0.8rem 1rem;
        box-shadow:0 10px 25px rgba(15,23,42,0.12);
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:0.75rem;
        font-size:0.86rem;
        font-weight:500;
    `;
    toast.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            ${getHeroicon(st.icon, "hi-icon")}
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" style="font-size:0.65rem" aria-label="Đóng"></button>
    `;
    toast.querySelector("button").addEventListener("click", () => toast.remove());
    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 3800);
}

// Thanh điều hướng dạng Sidebar dọc bên trái (Left Sidebar Navigation)
function renderNavbar(activePage = "shifts") {
    const mount = document.getElementById("app-navbar");
    if (!mount) return;
    const role = getCurrentRole();

    mount.innerHTML = `
        <!-- Thanh điều hướng dạng Sidebar dọc bên trái (Desktop & Tablet) -->
        <aside class="app-sidebar" id="app-sidebar" aria-label="Thanh điều hướng chính">
            <!-- 1. Đầu Sidebar: Thương hiệu ReconHub -->
            <div class="sidebar-header">
                <a href="index.html" class="sidebar-brand text-decoration-none">
                    <span class="modern-brand-logo">
                        ${getHeroicon("building-library", "hi-icon")}
                    </span>
                    <div class="sidebar-brand-text">
                        <span class="d-block fw-bold text-dark lh-1" style="font-size: 1.05rem;">ReconHub</span>
                        <small class="text-secondary fw-semibold uppercase" style="font-size: 0.65rem; letter-spacing: 0.08em;">RETAIL FINANCE</small>
                    </div>
                </a>
                <button type="button" class="btn-close d-lg-none" id="btn-close-sidebar" aria-label="Đóng menu"></button>
            </div>

            <!-- 2. Thân Sidebar: Danh sách phân hệ chức năng -->
            <div class="sidebar-nav-section">
                <div class="sidebar-section-label">CHỨC NĂNG CHÍNH</div>
                <nav class="sidebar-nav" aria-label="Menu chức năng">
                    <a href="index.html" class="sidebar-nav-tab ${activePage === "shifts" ? "active" : ""}">
                        ${getHeroicon("calendar", "hi-icon")}
                        <span class="sidebar-nav-text">Ca làm việc</span>
                    </a>
                    <a href="pos.html" class="sidebar-nav-tab ${activePage === "pos" ? "active" : ""}">
                        ${getHeroicon("computer-desktop", "hi-icon")}
                        <span class="sidebar-nav-text">Quầy thu ngân</span>
                    </a>
                    <a href="reconciliation.html" class="sidebar-nav-tab ${activePage === "reconcile" ? "active" : ""}">
                        ${getHeroicon("arrows-right-left", "hi-icon")}
                        <span class="sidebar-nav-text">Đối soát</span>
                    </a>
                    <a href="dashboard.html" class="sidebar-nav-tab ${activePage === "dashboard" ? "active" : ""}">
                        ${getHeroicon("chart-bar", "hi-icon")}
                        <span class="sidebar-nav-text">Báo cáo</span>
                    </a>
                    <a href="archive.html" class="sidebar-nav-tab ${activePage === "archive" ? "active" : ""}">
                        ${getHeroicon("archive-box", "hi-icon")}
                        <span class="sidebar-nav-text">Kho lưu trữ</span>
                    </a>
                    <a href="hubbie.html" class="sidebar-nav-tab ${activePage === "hubbie" ? "active" : ""}">
                        ${getHeroicon("sparkles", "hi-icon")}
                        <span class="sidebar-nav-text">Trợ lý AI (Hubbie)</span>
                    </a>
                </nav>
            </div>

            <!-- 3. Chân Sidebar: Bộ chọn Vai trò & Trạng thái sổ quỹ -->
            <div class="sidebar-footer">
                <div class="sidebar-role-panel">
                    <div class="d-flex align-items-center justify-content-between mb-1.5">
                        <span class="sidebar-role-label">VAI TRÒ SỬ DỤNG</span>
                        <button type="button" class="btn-sidebar-reset" onclick="resetDemoStore()" title="Khôi phục dữ liệu mặc định">
                            ↻
                        </button>
                    </div>
                    <select id="global-role-select" class="form-select sidebar-role-select" aria-label="Tài khoản sử dụng">
                        <option value="OWNER" ${role === "OWNER" ? "selected" : ""}>Chủ cửa hàng</option>
                        <option value="REVIEWER" ${role === "REVIEWER" ? "selected" : ""}>Kế toán</option>
                        <option value="CASHIER" ${role === "CASHIER" ? "selected" : ""}>Thu ngân</option>
                    </select>
                </div>

                <div class="sidebar-system-status">
                    <span class="status-dot-pulse"></span>
                    <span class="status-text">Sổ quỹ: Đã đồng bộ</span>
                </div>
            </div>
        </aside>

        <!-- Thanh Mobile Topbar dành cho màn hình nhỏ (< 992px) -->
        <div class="mobile-topbar d-lg-none">
            <button type="button" class="btn btn-sm btn-light border" id="btn-toggle-sidebar" aria-label="Mở menu">
                <svg class="hi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
            </button>
            <a href="index.html" class="d-flex align-items-center gap-2 text-decoration-none">
                <span class="modern-brand-logo" style="width: 32px; height: 32px; border-radius: 8px;">
                    ${getHeroicon("building-library", "hi-icon hi-icon-sm")}
                </span>
                <span class="fw-bold text-dark" style="font-size: 0.95rem;">ReconHub</span>
            </a>
            <span class="fp-badge fp-badge-neutral" style="font-size: 0.72rem;">${role}</span>
        </div>
        <div class="sidebar-backdrop d-lg-none" id="sidebar-backdrop"></div>
    `;

    const roleSelect = document.getElementById("global-role-select");
    if (roleSelect) {
        roleSelect.addEventListener("change", (e) => setCurrentRole(e.target.value));
    }

    // Toggle menu trên mobile
    const toggleBtn = document.getElementById("btn-toggle-sidebar");
    const closeBtn = document.getElementById("btn-close-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    const sidebar = document.getElementById("app-sidebar");

    const openSidebar = () => {
        sidebar?.classList.add("show-sidebar");
        backdrop?.classList.add("show");
    };
    const closeSidebar = () => {
        sidebar?.classList.remove("show-sidebar");
        backdrop?.classList.remove("show");
    };

    toggleBtn?.addEventListener("click", openSidebar);
    closeBtn?.addEventListener("click", closeSidebar);
    backdrop?.addEventListener("click", closeSidebar);
}

function renderFooter() {
    const mount = document.getElementById("app-footer");
    if (!mount) return;
    mount.innerHTML = `
        <footer class="app-main-footer border-top py-3 bg-white">
            <div class="container shift-page-wrapper d-flex flex-column flex-md-row align-items-center justify-content-between gap-2 text-secondary" style="font-size: 0.82rem;">
                <div><strong class="text-dark">VietQR ReconHub</strong> — Hệ thống quản lý bán hàng và đối soát thanh toán QR.</div>
                <div>Phiên bản dành cho Hộ kinh doanh &amp; Cửa hàng bán lẻ</div>
            </div>
        </footer>
    `;
}

function initPageAnimations() {
    // Tải trước (Prefetch) các trang trong thanh điều hướng để chuyển trang tức thì không độ trễ
    const pages = ["index.html", "pos.html", "reconciliation.html", "dashboard.html", "archive.html", "hubbie.html"];
    pages.forEach((page) => {
        if (!window.location.pathname.endsWith(page)) {
            const link = document.createElement("link");
            link.rel = "prefetch";
            link.href = page;
            document.head.appendChild(link);
        }
    });
}