# -*- coding: utf-8 -*-

with open("frontend/js/pos.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add formatTimeOnly function if not present
if "function formatTimeOnly" not in code:
    time_helper = """
function formatTimeOnly(dateStr) {
    if (!dateStr) return "--:--";
    const d = new Date(dateStr);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
"""
    code = time_helper + code

# 2. Update updatePosShiftLockState badge and header name
old_badge_block = """    if (badgeEl) {
        badgeEl.className = badgeClass;
        badgeEl.textContent = badgeText;
    }"""

new_badge_block = """    if (badgeEl) {
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
    }"""

code = code.replace(old_badge_block, new_badge_block)

# 3. Update updateSseStatusBadge
old_sse_fn = """function updateSseStatusBadge(isConnected) {
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
}"""

new_sse_fn = """function updateSseStatusBadge(isConnected) {
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
}"""

code = code.replace(old_sse_fn, new_sse_fn)

# 4. Update the tbody mapping in renderPosOrdersTable
old_tbody_pattern = """            return `
                <tr class="${isCancelled ? "table-light text-muted" : ""}">
                    <td>
                        <div class="d-flex align-items-center gap-1">
                            <span class="fw-bold ${isCancelled ? "text-muted text-decoration-line-through" : "text-dark"}">${escapePosHtml(ord.order_code)}</span>
                            <span class="badge bg-light text-secondary border" style="font-size:0.65rem">Ca ${ord.shift_id}</span>
                        </div>
                        <div class="text-secondary" style="font-size: 0.74rem;">
                            ${escapePosHtml(ord.note || formatDateTime(ord.created_at))}
                        </div>
                    </td>
                    <td class="text-end fw-bold font-numeric">
                        ${
                            isCancelled
                                ? `<span class="text-decoration-line-through text-muted">${formatVND(total)}</span>
                                   <div class="text-danger small" style="font-size:0.68rem">Không tính sổ quỹ</div>`
                                : formatVND(total)
                        }
                    </td>
                    <td class="text-end font-numeric">
                        ${
                            isCancelled
                                ? `<div class="text-muted small">—</div>`
                                : `<div class="fw-semibold text-success">${formatVND(paid)}</div>
                                   ${
                                       remaining > 0
                                           ? `<div class="text-warning small" style="font-size: 0.74rem;">Còn thiếu: <strong>${formatVND(remaining)}</strong></div>`
                                           : `<div class="text-secondary small" style="font-size: 0.74rem;">Hoàn tất</div>`
                                   }`
                        }
                    </td>
                    <td>
                        <div class="d-flex flex-column align-items-start gap-1">
                            ${
                                isCancelled
                                    ? `<span class="fp-badge fp-badge-danger">Đã hủy (Không tính sổ quỹ)</span>`
                                    : renderStatusBadge(ord.payment_status || "UNPAID")
                            }
                        </div>
                    </td>
                    <td class="text-end">
                        ${
                            isCancelled
                                ? `<button type="button" class="btn btn-sm btn-light border text-muted py-1 px-2" disabled style="font-size: 0.75rem;">
                                       Đã hủy đơn
                                   </button>`
                                : isPaid
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
            `;"""

new_tbody_pattern = """            const isPartial = !isPaid && paid > 0;

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
            `;"""

if old_tbody_pattern in code:
    code = code.replace(old_tbody_pattern, new_tbody_pattern)
    print("Replaced tbody mapping successfully.")
else:
    print("Warning: old_tbody_pattern not found via exact match.")

with open("frontend/js/pos.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated frontend/js/pos.js successfully.")
