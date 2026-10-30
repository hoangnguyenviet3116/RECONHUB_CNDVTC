// ==========================================================================
// VIETQR RECONHUB — AUTHENTICATION SERVICE & INTERFACE LOGIC
// ==========================================================================

const AUTH_API_URL = "http://localhost:8000";

// 1. Kiểm tra trạng thái đăng nhập
function getSessionToken() {
    return localStorage.getItem("reconhub_token");
}

function getStoredUser() {
    try {
        const raw = localStorage.getItem("recon_user");
        return raw ? JSON.parse(raw) : null;
    } catch (_) {
        return null;
    }
}

function saveAuthSession(authData) {
    if (!authData || !authData.token) return;
    localStorage.setItem("reconhub_token", authData.token);
    if (authData.user) {
        localStorage.setItem("recon_user", JSON.stringify(authData.user));
        localStorage.setItem("recon_role", authData.user.role || "OWNER");
        localStorage.setItem("recon_merchant_id", String(authData.user.merchant_id || 1));
    }
}

function logoutUser() {
    localStorage.removeItem("reconhub_token");
    localStorage.removeItem("recon_user");
    // Không xóa recon_role và recon_merchant_id để tương thích ngược nếu cần, hoặc reset về mặc định
    localStorage.setItem("recon_role", "OWNER");
    window.location.href = "login.html";
}

// 2. Xử lý Đăng nhập qua Form (Email & Password)
async function submitLogin(email, password) {
    const errorEl = document.getElementById("auth-error-alert");
    const submitBtn = document.getElementById("btn-submit-login");

    if (errorEl) errorEl.classList.add("d-none");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Đang xác thực...`;
    }

    try {
        const res = await fetch(`${AUTH_API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || "Đăng nhập không thành công.");
        }

        saveAuthSession(data);
        showAuthSuccess("Đăng nhập thành công! Đang chuyển hướng...");
        setTimeout(() => {
            window.location.href = "index.html";
        }, 600);
    } catch (err) {
        if (errorEl) {
            errorEl.textContent = err.message;
            errorEl.classList.remove("d-none");
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Đăng nhập hệ thống</span> <svg class="hi-icon ms-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"/></svg>`;
        }
    }
}

// 3. Đăng nhập nhanh 1-Click (Dành cho Demo / Khảo thí)
async function submitQuickLogin(demoRole) {
    const errorEl = document.getElementById("auth-error-alert");
    if (errorEl) errorEl.classList.add("d-none");

    const card = document.querySelector(`.demo-account-card[data-role="${demoRole}"]`);
    if (card) {
        card.classList.add("is-loading");
    }

    try {
        const res = await fetch(`${AUTH_API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ demo_role: demoRole })
        });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || "Không thể đăng nhập tài khoản demo.");
        }

        saveAuthSession(data);
        showAuthSuccess(`Đăng nhập với vai trò ${demoRole} thành công!`);
        setTimeout(() => {
            window.location.href = "index.html";
        }, 500);
    } catch (err) {
        if (errorEl) {
            errorEl.textContent = err.message;
            errorEl.classList.remove("d-none");
        }
    } finally {
        if (card) card.classList.remove("is-loading");
    }
}

// 4. Xử lý Đăng ký Cửa hàng & Tài khoản Mới
async function submitRegister(formData) {
    const errorEl = document.getElementById("auth-error-alert");
    const submitBtn = document.getElementById("btn-submit-register");

    if (errorEl) errorEl.classList.add("d-none");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Đang khởi tạo cửa hàng...`;
    }

    try {
        const res = await fetch(`${AUTH_API_URL}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || "Đăng ký không thành công.");
        }

        saveAuthSession(data);
        showAuthSuccess("Khởi tạo cửa hàng thành công! Đang vào hệ thống...");
        setTimeout(() => {
            window.location.href = "index.html";
        }, 800);
    } catch (err) {
        if (errorEl) {
            errorEl.textContent = err.message;
            errorEl.classList.remove("d-none");
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Hoàn tất &amp; Mở cửa hàng</span> <svg class="hi-icon ms-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"/></svg>`;
        }
    }
}

// 5. Hiển thị thông báo thành công
function showAuthSuccess(message) {
    const successEl = document.getElementById("auth-success-alert");
    if (successEl) {
        successEl.textContent = message;
        successEl.classList.remove("d-none");
    }
}

// 6. Tiện ích ẩn / hiện mật khẩu
function togglePasswordVisibility(inputId, toggleBtnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(toggleBtnId);
    if (!input || !btn) return;

    if (input.type === "password") {
        input.type = "text";
        btn.innerHTML = `<svg class="hi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88"/></svg>`;
    } else {
        input.type = "password";
        btn.innerHTML = `<svg class="hi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg>`;
    }
}
