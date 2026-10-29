# -*- coding: utf-8 -*-
import re

with open("frontend/js/api.js", "r", encoding="utf-8") as f:
    content = f.read()

# Add missing icons if not already present
new_icons = '''    "calendar": `<path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.253 3H3.75A2.25 2.25 0 0 0 1.5 7.5v11.25A2.25 2.25 0 0 0 3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V7.5A2.25 2.25 0 0 0 20.25 5.25H17.25M3.75 9h16.5" />`,
    "computer-desktop": `<path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0H3" />`,
    "building-library": `<path stroke-linecap="round" stroke-linejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z" />`,
    "arrows-right-left": `<path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />`,
    "chart-bar": `<path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />`,
    "lock-closed": `<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />`,'''

if '"calendar":' not in content:
    content = content.replace('const HEROICONS_PATHS = {', 'const HEROICONS_PATHS = {\n' + new_icons)

# Replace renderNavbar implementation
new_render_navbar = '''function renderNavbar(activePage = "shifts") {
    const mount = document.getElementById("app-navbar");
    if (!mount) return;
    const role = getCurrentRole();

    mount.innerHTML = `
        <header class="fp-navbar-modern">
            <div class="container d-flex flex-wrap align-items-center justify-content-between gap-3" style="max-width: 1160px;">
                <a href="index.html" class="fp-brand text-decoration-none">
                    <span class="modern-brand-logo">
                        ${getHeroicon("building-library", "hi-icon")}
                    </span>
                    <div>
                        <span class="d-block fw-bold text-dark lh-1" style="font-size: 1.05rem;">ReconHub</span>
                        <small class="text-secondary fw-semibold uppercase" style="font-size: 0.68rem; letter-spacing: 0.08em;">RETAIL FINANCE</small>
                    </div>
                </a>

                <nav class="d-flex align-items-center gap-1 flex-wrap" aria-label="Menu chức năng">
                    <a href="index.html" class="modern-nav-tab ${activePage === "shifts" ? "active" : ""}">
                        ${getHeroicon("calendar", "hi-icon")}
                        <span>Ca làm việc</span>
                    </a>
                    <a href="pos.html" class="modern-nav-tab ${activePage === "pos" ? "active" : ""}">
                        ${getHeroicon("computer-desktop", "hi-icon")}
                        <span>Quầy thu ngân</span>
                    </a>
                    <a href="bank-simulator.html" class="modern-nav-tab ${activePage === "simulator" ? "active" : ""}">
                        ${getHeroicon("building-library", "hi-icon")}
                        <span>Cổng thanh toán</span>
                    </a>
                    <a href="reconciliation.html" class="modern-nav-tab ${activePage === "reconcile" ? "active" : ""}">
                        ${getHeroicon("arrows-right-left", "hi-icon")}
                        <span>Đối soát</span>
                    </a>
                    <a href="dashboard.html" class="modern-nav-tab ${activePage === "dashboard" ? "active" : ""}">
                        ${getHeroicon("chart-bar", "hi-icon")}
                        <span>Báo cáo</span>
                    </a>
                </nav>

                <div class="d-flex align-items-center gap-2">
                    <div class="modern-role-box">
                        <span class="modern-role-label">Vai trò</span>
                        <select id="global-role-select" class="form-select modern-role-select" aria-label="Tài khoản sử dụng">
                            <option value="OWNER" ${role === "OWNER" ? "selected" : ""}>Chủ cửa hàng</option>
                            <option value="REVIEWER" ${role === "REVIEWER" ? "selected" : ""}>Kế toán</option>
                            <option value="CASHIER" ${role === "CASHIER" ? "selected" : ""}>Thu ngân</option>
                        </select>
                    </div>
                    <button type="button" class="btn btn-sm btn-light border text-secondary rounded-3" onclick="resetDemoStore()" title="Khôi phục dữ liệu mặc định">
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
}'''

# Replace old renderNavbar
content = re.sub(r'function renderNavbar\(activePage = "shifts"\) \{[\s\S]*?const roleSelect = document\.getElementById\("global-role-select"\);[\s\S]*?\}\s*\}', new_render_navbar, content)

with open("frontend/js/api.js", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated frontend/js/api.js successfully.")
