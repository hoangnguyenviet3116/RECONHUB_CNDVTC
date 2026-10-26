with open("frontend/js/bank_simulator.js", "r", encoding="utf-8") as f:
    content = f.read()

# Normalize line endings
content_norm = content.replace("\r\n", "\n")

target1 = """    const basePayload = {
        merchant_id: getCurrentMerchantId(),
        reference_code: referenceCode,
        amount: amount,
        transfer_content: transferContent,
        tamper_signature: testMode === "INVALID_HMAC",
        simulate_invalid_hmac: testMode === "INVALID_HMAC"
    };

    try {
        if (testMode === "CONCURRENT_DUPLICATE") {
            await Promise.allSettled([
                apiRequest("/mock-bank/trigger-transfer", { method: "POST", body: JSON.stringify(basePayload) }),
                apiRequest("/mock-bank/trigger-transfer", { method: "POST", body: JSON.stringify(basePayload) })
            ]);
            renderFriendlyReceipt({
                badgeText: "Chặn trùng lặp",
                isSuccess: true,
                title: "Đã ngăn chặn cộng tiền trùng 2 lần",
                message: `Giao dịch ${referenceCode} bị gửi lặp 2 lần nhưng hệ thống chỉ ghi nhận đúng 1 lần duy nhất.`,
                referenceCode,
                amount,
                transferContent
            });
        } else {
            const response = await apiRequest("/mock-bank/trigger-transfer", {
                method: "POST",
                body: JSON.stringify(basePayload)
            });
            renderFriendlyReceipt({
                badgeText: "Thành công",
                isSuccess: true,
                title: "Chuyển khoản thành công",
                message: response.message || "Đã tiếp nhận khoản chuyển khoản và tự động đối soát với hóa đơn.",
                referenceCode,
                amount,
                transferContent
            });
        }

        generateFreshReferenceCode();
        await loadBankTransactionsList(false);
        await loadOrdersForSimulatorSelect();
    } catch (error) {
        if (error.isNetworkError) {
            executeStoreTransferSimulation(basePayload, testMode);
        } else {
            renderFriendlyReceipt({
                badgeText: "Bị từ chối",
                isSuccess: false,
                title: "Giao dịch bị từ chối bảo mật",
                message: error.message || "Thông báo chuyển khoản không hợp lệ.",
                referenceCode,
                amount,
                transferContent
            });
            showToast(error.message, "danger");
        }
    }"""

replacement1 = """    const transferTime = new Date();
    const basePayload = {
        merchant_id: getCurrentMerchantId(),
        reference_code: referenceCode,
        amount: amount,
        transfer_content: transferContent,
        transfer_time: transferTime.toISOString(),
        transaction_date: transferTime.toISOString(),
        tamper_signature: testMode === "INVALID_HMAC",
        simulate_invalid_hmac: testMode === "INVALID_HMAC"
    };

    try {
        if (testMode === "CONCURRENT_DUPLICATE") {
            await Promise.allSettled([
                apiRequest("/mock-bank/trigger-transfer", { method: "POST", body: JSON.stringify(basePayload) }),
                apiRequest("/mock-bank/trigger-transfer", { method: "POST", body: JSON.stringify(basePayload) })
            ]);
            renderFriendlyReceipt({
                badgeText: "Chặn trùng lặp",
                isSuccess: true,
                title: "Đã ngăn chặn cộng tiền trùng 2 lần",
                message: `Giao dịch ${referenceCode} bị gửi lặp 2 lần nhưng hệ thống chỉ ghi nhận đúng 1 lần duy nhất.`,
                referenceCode,
                amount,
                transferContent,
                transferTime
            });
        } else {
            const response = await apiRequest("/mock-bank/trigger-transfer", {
                method: "POST",
                body: JSON.stringify(basePayload)
            });
            renderFriendlyReceipt({
                badgeText: "Thành công",
                isSuccess: true,
                title: "Chuyển khoản thành công",
                message: response.message || "Đã tiếp nhận khoản chuyển khoản và tự động đối soát với hóa đơn.",
                referenceCode,
                amount,
                transferContent,
                transferTime
            });
        }

        generateFreshReferenceCode();
        await loadBankTransactionsList(false);
        await loadOrdersForSimulatorSelect();
    } catch (error) {
        if (error.isNetworkError) {
            executeStoreTransferSimulation(basePayload, testMode, transferTime);
        } else {
            renderFriendlyReceipt({
                badgeText: "Bị từ chối",
                isSuccess: false,
                title: "Giao dịch bị từ chối bảo mật",
                message: error.message || "Thông báo chuyển khoản không hợp lệ.",
                referenceCode,
                amount,
                transferContent,
                transferTime
            });
            showToast(error.message, "danger");
        }
    }"""

target2 = """function executeStoreTransferSimulation(payload, testMode) {"""
replacement2 = """function executeStoreTransferSimulation(payload, testMode, transferTime = null) {"""

target3 = """function renderFriendlyReceipt({
    badgeText,
    isSuccess,
    title,
    message,
    referenceCode,
    amount,
    transferContent,
    allocated,
    unallocated,
    nextLinkHtml = ""
}) {"""

replacement3 = """function renderFriendlyReceipt({
    badgeText,
    isSuccess,
    title,
    message,
    referenceCode,
    amount,
    transferContent,
    allocated,
    unallocated,
    nextLinkHtml = "",
    transferTime = null
}) {"""

target4 = """        <div class="p-2 px-3 rounded-3 bg-white border">
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Mã GD:</span>
                <strong class="font-numeric">${escapeSimHtml(referenceCode)}</strong>
            </div>"""

replacement4 = """        <div class="p-2 px-3 rounded-3 bg-white border">
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Thời gian chuyển khoản:</span>
                <strong class="font-numeric text-dark">${formatDateTime(transferTime || new Date())}</strong>
            </div>
            <div class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-secondary">Mã GD:</span>
                <strong class="font-numeric">${escapeSimHtml(referenceCode)}</strong>
            </div>"""

assert target1 in content_norm, "Target 1 not found"
assert target2 in content_norm, "Target 2 not found"
assert target3 in content_norm, "Target 3 not found"
assert target4 in content_norm, "Target 4 not found"

content_norm = content_norm.replace(target1, replacement1)
content_norm = content_norm.replace(target2, replacement2)
content_norm = content_norm.replace(target3, replacement3)
content_norm = content_norm.replace(target4, replacement4)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open("frontend/js/bank_simulator.js", "w", encoding="utf-8") as f:
    f.write(content_norm)

print("SUCCESS: bank_simulator.js updated successfully")
