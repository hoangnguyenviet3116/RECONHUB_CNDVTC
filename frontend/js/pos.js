// ==========================================================================
// QUẦY THU NGÂN & PHÁT HÀNH MÃ VIETQR ĐỘNG (frontend/js/pos.js)
// ==========================================================================

let posOrdersCache = [];
let currentSelectedOrderForQr = null;
let posPollingTimer = null;
let isCreatingOrder = false;
let isInitialOrderLoad = true;

// 1. Khởi tạo màn hình Quầy thu ngân
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
        ttsToggle.addEventListener("change", (e) => {
            localStorage.setItem("recon_tts_enabled", String(e.target.checked));
            showToast(e.target.checked ? "Đã bật loa báo nhận tiền." : "Đã tắt loa báo nhận tiền.", "info");
        });
    }

    document.getElementById("btn-test-tts-paid")?.addEventListener("click", () => triggerDemoTtsScenario("PAID"));
    document.getElementById("btn-test-tts-partial")?.addEventListener("click", () => triggerDemoTtsScenario("PARTIAL"));
    document.getElementById("btn-test-tts-overpaid")?.addEventListener("click", () => triggerDemoTtsScenario("OVERPAID"));
}

// 3. Tải danh sách ca đang mở bán
async function loadOpenShiftsForPos() {
    const selectEl = document.getElementById("pos-shift-select");
    if (!selectEl) return;

    const urlParams = new URLSearchParams(window.location.search);
    const preferredShiftId = urlParams.get("shift_id");

    let shifts = [];
    try {
        const data = await apiRequest("/shifts");
        shifts = Array.isArray(data) ? data : (data.items || data.shifts || []);
    } catch (_) {
        shifts = getDemoStore().shifts || [];
    }

    const openShifts = shifts.filter((s) => String(s.status || "").toUpperCase() === "OPEN");
    if (openShifts.length > 0) {
        selectEl.innerHTML = openShifts
            .map(
                (s) =>
                    `<option value="${s.id}" ${String(s.id) === String(preferredShiftId) ? "selected" : ""}>
                        ${escapePosHtml(s.name)}
                    </option>`
            )
            .join("");
    }
}

// 4. Tải danh sách hóa đơn và kiểm tra phát loa thông báo
async function loadPosOrders(isManualRefresh = false, isFromPolling = false) {
    try {
        const ordersRes = await apiRequest("/orders");
        posOrdersCache = Array.isArray(ordersRes) ? ordersRes : (ordersRes.items || ordersRes.orders || []);
    } catch (_) {
        const store = getDemoStore();
        posOrdersCache = store.orders || [];
    }

    if (typeof announceOrderChangeIfNeeded === "function") {
        posOrdersCache.forEach((ord) => {
            announceOrderChangeIfNeeded(ord, { isInitialSnapshot: isInitialOrderLoad });
        });
    }
    isInitialOrderLoad = false;

    renderPosOrdersTable(posOrdersCache);

    // Nếu đang mở hộp thoại QR của đơn hàng mà đơn đó vừa được thanh toán xong thì cập nhật nhãn trên hộp thoại
    if (currentSelectedOrderForQr) {
        const updated = posOrdersCache.find((o) => Number(o.id) === Number(currentSelectedOrderForQr.id));
        if (updated) {
            currentSelectedOrderForQr = updated;
            const badgeEl = document.getElementById("modal-qr-status-badge");
            if (badgeEl && String(updated.payment_status).toUpperCase() === "PAID") {
                badgeEl.className = "fp-badge fp-badge-success mb-1";
                badgeEl.textContent = "✓ Đã thanh toán đủ";
            }
        }
    }

    if (isManualRefresh && !isFromPolling) {
        showToast("Đã làm mới danh sách hóa đơn.", "success");
    }
}

// 5. Tự động đồng bộ trạng thái đơn mỗi 2 giây
function startPosPolling() {
    if (posPollingTimer) clearInterval(posPollingTimer);
    posPollingTimer = setInterval(() => {
        if (document.hidden) return;
        loadPosOrders(false, true);
    }, 2000);
}

// 6. Hiển thị bảng danh sách hóa đơn trong ca
function renderPosOrdersTable(orders) {
    const tbody = document.getElementById("pos-orders-tbody");
    if (!tbody) return;

    const filterVal = document.getElementById("pos-filter-payment")?.value || "ALL";
    const searchVal = (document.getElementById("pos-search-order")?.value || "").trim().toUpperCase();

    const filtered = (orders || []).filter((ord) => {
        const payStatus = String(ord.payment_status || "UNPAID").toUpperCase();
        const code = String(ord.order_code || "").toUpperCase();
        const matchStatus = filterVal === "ALL" || payStatus === filterVal;
        const matchSearch = !searchVal || code.includes(searchVal);
        return matchStatus && matchSearch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-secondary">
                    Chưa có hóa đơn nào phù hợp.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered
        .map((ord) => {
            const total = Number(ord.total_amount || 0);
            const paid = Number(
                ord.net_paid_amount ??
                ord.allocated_amount ??
                (String(ord.payment_status).toUpperCase() === "PAID" ? total : 0)
            );
            const remaining = Math.max(0, total - paid);
            const qrObj = ord.qr_request || ord.active_payment_request || null;
            const qrStatus = qrObj ? qrObj.status : (ord.qr_status || "UNISSUED");
            const isPaid = String(ord.payment_status || "").toUpperCase() === "PAID";

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-dark">${escapePosHtml(ord.order_code)}</div>
                        <div class="text-secondary" style="font-size: 0.74rem;">
                            ${escapePosHtml(ord.note || formatDateTime(ord.created_at))}
                        </div>
                    </td>
                    <td class="text-end fw-bold font-numeric">
                        ${formatVND(total)}
                    </td>
                    <td class="text-end font-numeric">
                        <div class="fw-semibold text-success">${formatVND(paid)}</div>
                        ${
                            remaining > 0
                                ? `<div class="text-warning small" style="font-size: 0.74rem;">Còn thiếu: <strong>${formatVND(remaining)}</strong></div>`
                                : `<div class="text-secondary small" style="font-size: 0.74rem;">Hoàn tất</div>`
                        }
                    </td>
                    <td>
                        <div class="d-flex flex-column align-items-start gap-1">
                            ${renderStatusBadge(ord.payment_status || "UNPAID")}
                        </div>
                    </td>
                    <td class="text-end">
                        ${
                            isPaid
                                ? `<button type="button" class="btn-fp-outline py-1 px-3" style="font-size: 0.78rem;" onclick="openOrderQrModal(${ord.id}, false)">
                                       Xem biên lai
                                   </button>`
                                : `<button type="button" class="btn-fp-dark py-1 px-3" style="font-size: 0.78rem;" onclick="openOrderQrModal(${ord.id}, true)">
                                       ${getHeroicon("qr-code", "hi-icon hi-icon-sm")}
                                       <span>${qrStatus === "ACTIVE" ? "Hiện mã QR" : "Xuất mã QR"}</span>
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
    const accountNo = "0123456789";
    const amount = Math.round(Number(expectedAmount || 0));
    const addInfo = encodeURIComponent(`TT ${orderCode}`);
    const accountName = encodeURIComponent("VIETQR RECONHUB");
    return `https://img.vietqr.io/image/${bankBin}-${accountNo}-compact2.png?amount=${amount}&addInfo=${addInfo}&accountName=${accountName}`;
}

async function openOrderQrModal(orderId, shouldIssueIfMissing = true) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    currentSelectedOrderForQr = order;
    const existingQr = order.qr_request || order.active_payment_request;

    if (shouldIssueIfMissing && (!existingQr || existingQr.status !== "ACTIVE")) {
        await issueDynamicVietQr(order.id, false);
    } else {
        displayQrInModal(order, existingQr);
    }
}

async function issueDynamicVietQr(orderId, isReissue = false) {
    const order = posOrdersCache.find((o) => Number(o.id) === Number(orderId));
    if (!order) return;

    const remainingAmount = Math.max(0, Number(order.total_amount || 0) - Number(order.net_paid_amount || 0));
    const expected = remainingAmount > 0 ? remainingAmount : order.total_amount;

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

    const expectedAmount =
        qrData?.expected_amount ??
        Math.max(0, Number(order.total_amount || 0) - Number(order.net_paid_amount || 0)) ??
        order.total_amount;

    const qrUrl = qrData?.qr_url || buildEmvcoVietQrUrl(order.order_code, expectedAmount);
    const isPaid = String(order.payment_status || "").toUpperCase() === "PAID";

    const badgeEl = document.getElementById("modal-qr-status-badge");
    if (badgeEl) {
        badgeEl.className = `fp-badge ${isPaid ? "fp-badge-success" : "fp-badge-dark"} mb-1`;
        badgeEl.textContent = isPaid ? "✓ Đã thanh toán đủ" : "Mã QR đang hoạt động";
    }

    const imgEl = document.getElementById("modal-qr-image");
    const ordCodeEl = document.getElementById("modal-qr-order-code");
    const amountEl = document.getElementById("modal-qr-expected-amount");
    const contentEl = document.getElementById("modal-qr-transfer-content");
    const simLinkEl = document.getElementById("modal-link-simulator");

    if (imgEl) imgEl.src = qrUrl;
    if (ordCodeEl) ordCodeEl.textContent = order.order_code;
    if (amountEl) amountEl.textContent = formatVND(expectedAmount);
    if (contentEl) contentEl.textContent = `TT ${order.order_code}`;

    if (simLinkEl) {
        simLinkEl.href = `bank-simulator.html?order_code=${encodeURIComponent(order.order_code)}&amount=${encodeURIComponent(expectedAmount)}`;
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