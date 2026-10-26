import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Update frontend/reconciliation.html
with open("frontend/reconciliation.html", "r", encoding="utf-8") as f:
    html = f.read()

html_norm = html.replace("\r\n", "\n")

target_tab_btn = """                        <button class="nav-link active fw-semibold small py-2 px-3" id="tab-unmatched-btn" data-bs-toggle="pill" data-bs-target="#pane-unmatched" type="button" role="tab">
                            Khoản tiền chờ ghép đơn"""
replacement_tab_btn = """                        <button class="nav-link active fw-semibold small py-2 px-3" id="tab-unmatched-btn" data-bs-toggle="pill" data-bs-target="#pane-unmatched" type="button" role="tab">
                            Khoản tiền chờ xử lý"""

assert target_tab_btn in html_norm, "target_tab_btn not found"
html_norm = html_norm.replace(target_tab_btn, replacement_tab_btn)

target_tab_comment = """                    <!-- TAB 1: DANH SÁCH GIAO DỊCH CHỜ GHÉP ĐƠN -->"""
replacement_tab_comment = """                    <!-- TAB 1: DANH SÁCH GIAO DỊCH CHỜ XỬ LÝ -->"""
assert target_tab_comment in html_norm, "target_tab_comment not found"
html_norm = html_norm.replace(target_tab_comment, replacement_tab_comment)

target_th = """                                        <th class="text-end">Số tiền chờ ghép</th>"""
replacement_th = """                                        <th class="text-end">Số tiền chờ xử lý</th>"""
assert target_th in html_norm, "target_th not found"
html_norm = html_norm.replace(target_th, replacement_th)

target_label_unalloc = """                                <span class="text-secondary">Số tiền còn chờ ghép:</span>"""
replacement_label_unalloc = """                                <span class="text-secondary">Số tiền chờ xử lý:</span>"""
assert target_label_unalloc in html_norm, "target_label_unalloc not found"
html_norm = html_norm.replace(target_label_unalloc, replacement_label_unalloc)

if "\r\n" in html:
    html_norm = html_norm.replace("\n", "\r\n")

with open("frontend/reconciliation.html", "w", encoding="utf-8") as f:
    f.write(html_norm)

print("SUCCESS: frontend/reconciliation.html updated")


# 2. Update frontend/js/reconciliation.js
with open("frontend/js/reconciliation.js", "r", encoding="utf-8") as f:
    js = f.read()

js_norm = js.replace("\r\n", "\n")

target_render_fn = """// 1. Bảng các khoản tiền chờ ghép đơn
function renderUnmatchedTable() {
    const tbody = document.getElementById("recon-unmatched-tbody");
    const countBadge = document.getElementById("badge-unmatched-count");
    if (!tbody) return;

    const exceptionTxs = (reconBankTxs || []).filter(
        (tx) =>
            Number(tx.unallocated_amount || 0) > 0 ||
            String(tx.match_status || "").toUpperCase() === "UNMATCHED"
    );

    if (countBadge) {
        countBadge.textContent = String(exceptionTxs.length);
    }

    if (exceptionTxs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-success fw-medium">
                    ✓ Tất cả các khoản chuyển khoản đã được khớp vào hóa đơn (Không có khoản tiền lệch).
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = exceptionTxs
        .map((tx) => {
            const unalloc = Number(tx.unallocated_amount || 0);
            const isHandled = Boolean(
                tx.is_handled ||
                (reconDecisions && reconDecisions.some((d) => Number(d.bank_transaction_id) === Number(tx.id)))
            );

            return `
                <tr id="row-recon-tx-${tx.id}">
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(tx.reference_code)}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(tx.created_at)}</div>
                    </td>
                    <td>
                        <span class="fw-medium text-dark">${escapeReconHtml(tx.transfer_content)}</span>
                    </td>
                    <td class="text-end font-numeric">
                        ${formatVND(tx.amount)}
                    </td>
                    <td class="text-end fw-bold text-danger font-numeric">
                        ${formatVND(unalloc)}
                    </td>
                    <td>
                        ${renderStatusBadge(tx.match_status || "UNMATCHED")}
                    </td>
                    <td class="text-end" id="action-cell-tx-${tx.id}">
                        ${
                            isHandled
                                ? `<button type="button" class="btn btn-sm btn-success py-1 px-3" disabled style="font-size: 0.8rem; background-color: #198754; border-color: #198754; color: #fff; cursor: default; opacity: 1;">
                                       ✓ Đã xử lý
                                   </button>`
                                : `<button type="button" class="btn-fp-dark py-1 px-3" id="btn-handle-tx-${tx.id}" style="font-size: 0.8rem;" onclick="handleTransactionAction(${tx.id})">
                                       Xử lý
                                   </button>`
                        }
                    </td>
                </tr>
            `;
        })
        .join("");
}"""

replacement_render_fn = """// 1. Bảng các khoản tiền chờ xử lý
function renderUnmatchedTable() {
    const tbody = document.getElementById("recon-unmatched-tbody");
    const countBadge = document.getElementById("badge-unmatched-count");
    if (!tbody) return;

    // Các khoản đã được xử lý sẽ không hiện ở tab chờ xử lý nữa
    const pendingTxs = (reconBankTxs || []).filter((tx) => {
        const isHandled = Boolean(
            tx.is_handled ||
            (reconDecisions && reconDecisions.some((d) => Number(d.bank_transaction_id) === Number(tx.id)))
        );
        if (isHandled) return false;
        return Number(tx.unallocated_amount || 0) > 0 || String(tx.match_status || "").toUpperCase() === "UNMATCHED";
    });

    if (countBadge) {
        countBadge.textContent = String(pendingTxs.length);
    }

    if (pendingTxs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-success fw-medium">
                    ✓ Tất cả các khoản chuyển khoản đã được xử lý hoàn tất (Không còn khoản tiền chờ xử lý).
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = pendingTxs
        .map((tx) => {
            const unalloc = Number(tx.unallocated_amount || 0);

            return `
                <tr id="row-recon-tx-${tx.id}">
                    <td>
                        <div class="fw-bold text-dark font-numeric">${escapeReconHtml(tx.reference_code)}</div>
                        <div class="text-secondary" style="font-size: 0.72rem;">${formatDateTime(tx.created_at)}</div>
                    </td>
                    <td>
                        <span class="fw-medium text-dark">${escapeReconHtml(tx.transfer_content)}</span>
                    </td>
                    <td class="text-end font-numeric">
                        ${formatVND(tx.amount)}
                    </td>
                    <td class="text-end fw-bold text-danger font-numeric">
                        ${formatVND(unalloc)}
                    </td>
                    <td>
                        ${renderStatusBadge(tx.match_status || "UNMATCHED")}
                    </td>
                    <td class="text-end" id="action-cell-tx-${tx.id}">
                        <button type="button" class="btn-fp-dark py-1 px-3" id="btn-handle-tx-${tx.id}" style="font-size: 0.8rem;" onclick="handleTransactionAction(${tx.id})">
                            Xử lý
                        </button>
                    </td>
                </tr>
            `;
        })
        .join("");
}"""

assert target_render_fn in js_norm, "target_render_fn not found"
js_norm = js_norm.replace(target_render_fn, replacement_render_fn)

# In handleOverpaymentSubmit: when done, re-render renderUnmatchedTable immediately
target_ovp_finish = """        // 2. Cập nhật nút thành "Đã xử lý" (màu xanh, vô hiệu hóa) trên giao diện ngay lập tức
        const actionCell = document.getElementById(`action-cell-tx-${txId}`);
        if (actionCell) {
            actionCell.innerHTML = `
                <button type="button" class="btn btn-sm btn-success py-1 px-3" disabled style="font-size: 0.8rem; background-color: #198754; border-color: #198754; color: #fff; cursor: default; opacity: 1;">
                    ✓ Đã xử lý
                </button>
            `;
        }

        // 3. Đánh dấu tx trong bộ nhớ là đã xử lý
        const targetTx = reconBankTxs.find((t) => Number(t.id) === txId);
        if (targetTx) {
            targetTx.is_handled = true;
            targetTx.handling_method = methodPlan;
        }

        // 4. Ghi nhận vào lịch sử phê duyệt
        reconDecisions.unshift({
            id: resp.decision_id || Date.now(),
            order_id: orderId,
            order_code: resp.order_code || (targetTx ? targetTx.order_code : null),
            bank_transaction_id: txId,
            reference_code: resp.reference_code || (targetTx ? targetTx.reference_code : null),
            tx_amount: targetTx ? targetTx.amount : null,
            allocated_amount: targetTx ? targetTx.allocated_amount : null,
            unallocated_amount: targetTx ? targetTx.unallocated_amount : null,
            reviewer_id: getCurrentUserId(),
            reviewer_name: "Quản trị viên",
            decision_type: "OVERPAYMENT_RESOLUTION",
            reason: methodPlan,
            biometric_verified: securityMode === "WEBAUTHN_SIGN",
            review_date: new Date().toISOString()
        });
        renderDecisionsHistory();"""

replacement_ovp_finish = """        // 2. Đánh dấu tx trong bộ nhớ là đã xử lý
        const targetTx = reconBankTxs.find((t) => Number(t.id) === txId);
        if (targetTx) {
            targetTx.is_handled = true;
            targetTx.handling_method = methodPlan;
        }

        // 3. Ghi nhận vào lịch sử phê duyệt
        reconDecisions.unshift({
            id: resp.decision_id || Date.now(),
            order_id: orderId,
            order_code: resp.order_code || (targetTx ? targetTx.order_code : null),
            bank_transaction_id: txId,
            reference_code: resp.reference_code || (targetTx ? targetTx.reference_code : null),
            tx_amount: targetTx ? targetTx.amount : null,
            allocated_amount: targetTx ? targetTx.allocated_amount : null,
            unallocated_amount: targetTx ? targetTx.unallocated_amount : null,
            reviewer_id: getCurrentUserId(),
            reviewer_name: "Quản trị viên",
            decision_type: "OVERPAYMENT_RESOLUTION",
            reason: methodPlan,
            biometric_verified: securityMode === "WEBAUTHN_SIGN",
            review_date: new Date().toISOString()
        });

        // 4. Các khoản đã xử lý sẽ không hiện ở tab chờ xử lý nữa
        renderUnmatchedTable();
        renderDecisionsHistory();"""

assert target_ovp_finish in js_norm, "target_ovp_finish not found"
js_norm = js_norm.replace(target_ovp_finish, replacement_ovp_finish)

# In handleManualMatchSubmit: update renderUnmatchedTable
target_manual_finish = """    // Cập nhật nút thành Đã xử lý ngay lập tức trên giao diện
    const actionCell = document.getElementById(`action-cell-tx-${bankTxId}`);
    if (actionCell) {
        actionCell.innerHTML = `
            <button type="button" class="btn btn-sm btn-success py-1 px-3" disabled style="font-size: 0.8rem; background-color: #198754; border-color: #198754; color: #fff; cursor: default; opacity: 1;">
                ✓ Đã xử lý
            </button>
        `;
    }

    const targetTx = reconBankTxs.find((t) => Number(t.id) === bankTxId);
    if (targetTx) {
        targetTx.is_handled = true;
    }"""

replacement_manual_finish = """    const targetTx = reconBankTxs.find((t) => Number(t.id) === bankTxId);
    if (targetTx) {
        targetTx.is_handled = true;
    }
    // Các khoản đã xử lý sẽ không hiện ở tab chờ xử lý nữa
    renderUnmatchedTable();"""

assert target_manual_finish in js_norm, "target_manual_finish not found"
js_norm = js_norm.replace(target_manual_finish, replacement_manual_finish)

# Update toast on reverse
target_reverse_toast = """showToast("Đã hoàn đảo giao dịch về danh sách chờ ghép đơn!", "success");"""
replacement_reverse_toast = """showToast("Đã hoàn đảo giao dịch về danh sách chờ xử lý!", "success");"""
if target_reverse_toast in js_norm:
    js_norm = js_norm.replace(target_reverse_toast, replacement_reverse_toast)

if "\r\n" in js:
    js_norm = js_norm.replace("\n", "\r\n")

with open("frontend/js/reconciliation.js", "w", encoding="utf-8") as f:
    f.write(js_norm)

print("SUCCESS: frontend/js/reconciliation.js updated")
