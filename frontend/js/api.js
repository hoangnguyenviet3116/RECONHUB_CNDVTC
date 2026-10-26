// ==========================================================================
// VIETQR RECONHUB — KẾT NỐI API & TIỆN ÍCH HỆ THỐNG DÙNG CHUNG
// ==========================================================================

const API_BASE_URL = "http://localhost:8000";
const DEMO_STORE_KEY = "reconhub_live_store_v3";

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

    const netAllocated = (store.allocations || []).reduce((s, a) => s + Number(a.allocated_amount || 0), 0);
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
    "document-text": `<path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"/>`
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

// Thanh điều hướng chuẩn Web App thực tế (Không có banner nhắc bài)
// Thanh điều hướng chuẩn Web App thực tế (4 phân hệ cửa hàng, ẩn Cổng thanh toán mô phỏng)
function renderNavbar(activePage = "shifts") {
    const mount = document.getElementById("app-navbar");
    if (!mount) return;
    const role = getCurrentRole();

    mount.innerHTML = `
        <header class="fp-navbar">
            <div class="container d-flex flex-wrap align-items-center justify-content-between gap-3">
                <a href="index.html" class="fp-brand">
                    <span class="fp-brand-mark">${getHeroicon("banknotes", "hi-icon")}</span>
                    <div>
                        <span class="d-block lh-1">VietQR ReconHub</span>
                        <small class="text-secondary fw-normal" style="font-size: 0.72rem;">Quản lý thanh toán &amp; đối soát</small>
                    </div>
                </a>

                <nav class="step-pills-row flex-grow-1" style="max-width: 580px; grid-template-columns: repeat(4, 1fr);" aria-label="Menu chức năng">
                    <a href="index.html" class="step-pill-item justify-content-center ${activePage === "shifts" ? "active" : ""}">
                        <span>Ca làm việc</span>
                    </a>
                    <a href="pos.html" class="step-pill-item justify-content-center ${activePage === "pos" ? "active" : ""}">
                        <span>Quầy thu ngân</span>
                    </a>
                    <a href="reconciliation.html" class="step-pill-item justify-content-center ${activePage === "reconcile" ? "active" : ""}">
                        <span>Đối soát lệch</span>
                    </a>
                    <a href="dashboard.html" class="step-pill-item justify-content-center ${activePage === "dashboard" ? "active" : ""}">
                        <span>Báo cáo &amp; Sổ quỹ</span>
                    </a>
                </nav>

                <div class="d-flex align-items-center gap-2">
                    <select id="global-role-select" class="role-pill-select" aria-label="Tài khoản sử dụng">
                        <option value="CASHIER" ${role === "CASHIER" ? "selected" : ""}>Thu ngân</option>
                        <option value="REVIEWER" ${role === "REVIEWER" ? "selected" : ""}>Kế toán</option>
                        <option value="OWNER" ${role === "OWNER" ? "selected" : ""}>Chủ cửa hàng</option>
                    </select>
                    <button type="button" class="btn btn-sm btn-light border text-secondary" onclick="resetDemoStore()" title="Khôi phục dữ liệu mặc định">
                        ↻
                    </button>
                </div>
            </div>
        </header>
    `;

    const roleSelect = document.getElementById("global-role-select");
    if (roleSelect) {
        roleSelect.addEventListener("change", (e) => setCurrentRole(e.target.value));
    }
}

function renderFooter() {
    const mount = document.getElementById("app-footer");
    if (!mount) return;
    mount.innerHTML = `
        <footer class="border-top py-3 mt-5 bg-white">
            <div class="container d-flex flex-column flex-md-row align-items-center justify-content-between gap-2 small text-secondary">
                <div><strong class="text-dark">VietQR ReconHub</strong> — Hệ thống quản lý bán hàng và đối soát thanh toán QR.</div>
                <div>Phiên bản dành cho Hộ kinh doanh &amp; Cửa hàng bán lẻ</div>
            </div>
        </footer>
    `;
}

function initPageAnimations() {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || !window.gsap) return;
    const cards = document.querySelectorAll("[data-gsap='card']");
    if (cards.length > 0) {
        window.gsap.fromTo(
            cards,
            { autoAlpha: 0, y: 10 },
            { autoAlpha: 1, y: 0, duration: 0.35, stagger: 0.05, ease: "power2.out" }
        );
    }
}