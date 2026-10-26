with open("frontend/js/bank_simulator.js", "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

target1 = """    if (testMode === "INVALID_HMAC") {
        renderFriendlyReceipt({
            badgeText: "Chặn bảo mật",
            isSuccess: false,
            title: "Đã chặn bản tin sai chữ ký xác thực",
            message: "Bản tin báo có không khớp chữ ký bảo mật của ngân hàng nên không được ghi nhận vào sổ quỹ.",
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content
        });"""

replacement1 = """    if (testMode === "INVALID_HMAC") {
        renderFriendlyReceipt({
            badgeText: "Chặn bảo mật",
            isSuccess: false,
            title: "Đã chặn bản tin sai chữ ký xác thực",
            message: "Bản tin báo có không khớp chữ ký bảo mật của ngân hàng nên không được ghi nhận vào sổ quỹ.",
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content,
            transferTime
        });"""

target2 = """    if (exists) {
        renderFriendlyReceipt({
            badgeText: "Đã chặn trùng",
            isSuccess: false,
            title: "Mã giao dịch này đã được xử lý trước đó",
            message: `Mã giao dịch ${payload.reference_code} đã tồn tại trong sổ quỹ, hệ thống từ chối cộng tiền lần 2.`,
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content
        });"""

replacement2 = """    if (exists) {
        renderFriendlyReceipt({
            badgeText: "Đã chặn trùng",
            isSuccess: false,
            title: "Mã giao dịch này đã được xử lý trước đó",
            message: `Mã giao dịch ${payload.reference_code} đã tồn tại trong sổ quỹ, hệ thống từ chối cộng tiền lần 2.`,
            referenceCode: payload.reference_code,
            amount: payload.amount,
            transferContent: payload.transfer_content,
            transferTime
        });"""

target3 = """            created_at: new Date().toISOString(),
            is_valid: true
        });"""

replacement3 = """            created_at: (transferTime || new Date()).toISOString(),
            is_valid: true
        });"""

target4 = """        match_status: matchStatus,
        created_at: new Date().toISOString()
    };"""

replacement4 = """        match_status: matchStatus,
        created_at: (transferTime || new Date()).toISOString()
    };"""

target5 = """    renderFriendlyReceipt({
        badgeText: matchStatus === "UNMATCHED" ? "Chờ ghép đơn" : "Đã đối soát",
        isSuccess: true,
        title,
        message,
        referenceCode: payload.reference_code,
        amount: payload.amount,
        transferContent: payload.transfer_content,
        allocated,
        unallocated,
        nextLinkHtml
    });"""

replacement5 = """    renderFriendlyReceipt({
        badgeText: matchStatus === "UNMATCHED" ? "Chờ ghép đơn" : "Đã đối soát",
        isSuccess: true,
        title,
        message,
        referenceCode: payload.reference_code,
        amount: payload.amount,
        transferContent: payload.transfer_content,
        allocated,
        unallocated,
        nextLinkHtml,
        transferTime
    });"""

assert target1 in content_norm, "Target 1 not found"
assert target2 in content_norm, "Target 2 not found"
assert target3 in content_norm, "Target 3 not found"
assert target4 in content_norm, "Target 4 not found"
assert target5 in content_norm, "Target 5 not found"

content_norm = content_norm.replace(target1, replacement1)
content_norm = content_norm.replace(target2, replacement2)
content_norm = content_norm.replace(target3, replacement3)
content_norm = content_norm.replace(target4, replacement4)
content_norm = content_norm.replace(target5, replacement5)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open("frontend/js/bank_simulator.js", "w", encoding="utf-8") as f:
    f.write(content_norm)

print("SUCCESS: bank_simulator.js simulation helper updated")
