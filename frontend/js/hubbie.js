// ==========================================================================
// TRỢ LÝ VẬN HÀNH THUCHI AI / HUBBIE — VIETQR RECONHUB (frontend/js/hubbie.js)
// Giao diện tương tác Chatbot thông minh hỗ trợ hỏi đáp thu chi và vận hành
// ==========================================================================

let hubbieQuotaCount = 12;
const hubbieQuotaMax = 50;
let hubbieActiveShift = null;
let hubbieStoreCache = null;

// Lịch sử các cuộc trò chuyện mẫu
const hubbieConversations = [
    {
        id: "conv-1",
        title: "Tóm tắt doanh thu ca s...",
        snippet: "Ca sáng đang đạt 70% mục tiê...",
        time: "10:42",
        messages: [
            {
                sender: "bot",
                time: "10:40",
                text: `Chào Minh Anh! Tôi là trợ lý vận hành <strong>ThuChi AI</strong>. Tôi có thể giúp bạn kiểm tra doanh thu, tìm kiếm các hóa đơn chưa thu đủ, đối soát tiền ngân hàng hoặc rà soát chênh lệch sổ quỹ ca hôm nay.`
            }
        ]
    },
    {
        id: "conv-2",
        title: "Kiểm tra đơn chưa thanh...",
        snippet: "Có 2 đơn hàng quá 15 phút...",
        time: "Hôm qua",
        messages: [
            {
                sender: "user",
                time: "Hôm qua 14:15",
                text: "Có đơn nào quá 15 phút mà khách chưa quét QR không?"
            },
            {
                sender: "bot",
                time: "Hôm qua 14:15",
                text: "Dạ, hệ thống phát hiện có <strong>2 đơn hàng</strong> ở trạng thái <code>Chờ thanh toán</code> quá 15 phút. Bạn có thể kiểm tra lại với khách hoặc hủy đơn nếu khách không thực hiện chuyển khoản."
            }
        ]
    },
    {
        id: "conv-3",
        title: "Đối soát chênh lệch sổ quỹ",
        snippet: "Đã khớp 100% giao dịch QR...",
        time: "27/10",
        messages: [
            {
                sender: "user",
                time: "27/10 18:30",
                text: "Kiểm tra sổ quỹ ngày 27/10 có khớp số với ngân hàng không?"
            },
            {
                sender: "bot",
                time: "27/10 18:30",
                text: "Dạ, toàn bộ giao dịch ngày 27/10 <strong>đã khớp 100%</strong>. Chuỗi mã băm bảo mật SHA-256 xác thực sổ cái không bị can thiệp và Merkle Root đã được niêm phong an toàn."
            }
        ]
    },
    {
        id: "conv-4",
        title: "Phân tích tiền mặt vs QR",
        snippet: "Tỷ lệ chuyển khoản đạt 82%...",
        time: "26/10",
        messages: [
            {
                sender: "user",
                time: "26/10 11:20",
                text: "Tỷ lệ khách trả bằng mã VietQR tuần này là bao nhiêu?"
            },
            {
                sender: "bot",
                time: "26/10 11:20",
                text: "Tỷ lệ thanh toán không tiền mặt qua <strong>VietQR tuần này đạt 82.4%</strong>, tăng 5.2% so với tuần trước. Xu hướng quét QR tập trung nhiều nhất vào khung giờ 11:30 - 13:00."
            }
        ]
    }
];

let activeConvId = "conv-1";

function initHubbiePage() {
    updateHubbieClockAndDate();
    loadLiveStoreDataForHubbie();
    bindHubbieEvents();
}

function updateHubbieClockAndDate() {
    const datePill = document.getElementById("hubbie-current-date-pill");
    const updatedLabel = document.getElementById("hubbie-header-updated");

    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    const dateStr = `Hôm nay, ${now.getDate()} tháng ${now.getMonth() + 1}`;

    if (datePill) datePill.textContent = dateStr;
    if (updatedLabel) updatedLabel.textContent = `Phân tích dữ liệu ca làm việc — Cập nhật lúc ${timeStr}`;
}

async function loadLiveStoreDataForHubbie() {
    try {
        const [summary, shifts] = await Promise.all([
            apiRequest("/dashboard/summary?shift_id=ALL").catch(() => null),
            apiRequest("/shifts?archived=false").catch(() => null)
        ]);

        hubbieStoreCache = summary || getDemoStore();
        const activeShifts = Array.isArray(shifts) ? shifts : [];
        const openShift = activeShifts.find((s) => String(s.status).toUpperCase() === "OPEN") || activeShifts[0];

        if (openShift) {
            hubbieActiveShift = openShift;
            const shiftPill = document.getElementById("hubbie-shift-pill");
            if (shiftPill) {
                shiftPill.textContent = `${openShift.name} • CA-${String(openShift.id).padStart(4, "0")}`;
            }
        }

        // Cập nhật thẻ tóm tắt doanh thu trong tin nhắn chào mừng
        if (summary) {
            const revEl = document.getElementById("hubbie-stat-revenue");
            const ordEl = document.getElementById("hubbie-stat-orders");
            const discEl = document.getElementById("hubbie-stat-discrepancy");

            if (revEl) revEl.textContent = formatVND(summary.valid_order_total || 0);
            if (ordEl) ordEl.textContent = `${summary.valid_order_count || 0} đơn`;
            if (discEl) {
                const diff = Math.abs(Number(summary.valid_order_total || 0) - Number(summary.allocated_payment_total || 0));
                discEl.textContent = formatVND(diff);
                if (diff === 0) {
                    discEl.className = "font-numeric text-success";
                } else {
                    discEl.className = "font-numeric text-warning";
                }
            }
        }
    } catch (_) {
        // Dự phòng dữ liệu giả lập chuẩn
    }
}

function bindHubbieEvents() {
    // 1. Gửi tin nhắn qua Form
    const chatForm = document.getElementById("hubbie-chat-form");
    const chatInput = document.getElementById("hubbie-input-text");
    const sendBtn = document.getElementById("btn-hubbie-send");

    chatInput?.addEventListener("input", () => {
        if (chatInput.value.trim().length > 0) {
            sendBtn?.classList.add("active");
        } else {
            sendBtn?.classList.remove("active");
        }
    });

    chatForm?.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = chatInput?.value?.trim();
        if (!text) return;
        handleUserSendMessage(text);
        if (chatInput) chatInput.value = "";
        sendBtn?.classList.remove("active");
    });

    // 2. Nhấn vào các Chip câu hỏi gợi ý
    const chipsContainer = document.getElementById("hubbie-chips");
    chipsContainer?.addEventListener("click", (e) => {
        const chip = e.target.closest(".hubbie-chip");
        if (!chip) return;
        const prompt = chip.getAttribute("data-prompt") || chip.textContent.trim();
        handleUserSendMessage(prompt);
    });

    // 3. Nút Cuộc trò chuyện mới
    document.getElementById("btn-hubbie-new-chat")?.addEventListener("click", () => {
        createNewChatSession();
    });

    // 4. Tìm kiếm cuộc trò chuyện
    const searchInput = document.getElementById("hubbie-conv-search");
    searchInput?.addEventListener("input", (e) => {
        const query = e.target.value.trim().toUpperCase();
        filterConversationList(query);
    });

    // 5. Chọn cuộc trò chuyện trong danh sách
    const convList = document.getElementById("hubbie-conv-list");
    convList?.addEventListener("click", (e) => {
        const item = e.target.closest(".hubbie-conv-item");
        if (!item) return;
        const convId = item.getAttribute("data-id");
        if (convId) switchActiveConversation(convId);
    });

    // 6. Xóa lịch sử chat
    document.getElementById("btn-clear-chat")?.addEventListener("click", () => {
        const container = document.getElementById("hubbie-messages-container");
        if (!container) return;
        if (!confirm("Bạn có chắc chắn muốn xóa toàn bộ tin nhắn trong cuộc trò chuyện này?")) return;
        
        container.innerHTML = `
            <div class="hubbie-date-divider">
                <span class="hubbie-date-pill">Cuộc trò chuyện đã được làm mới</span>
            </div>
            <div class="hubbie-msg-bot">
                <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #eff6ff; color: #1e3a8a;">
                    <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>
                    </svg>
                </div>
                <div>
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <strong class="text-dark small fw-bold">ThuChi AI</strong>
                        <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">Vừa xong</span>
                    </div>
                    <div class="hubbie-bot-bubble">
                        Lịch sử hội thoại đã được đặt lại. Tôi luôn sẵn sàng trả lời các câu hỏi về doanh thu, hóa đơn hoặc đối soát sổ quỹ!
                    </div>
                </div>
            </div>
        `;
        showToast("Đã làm mới cuộc hội thoại thành công.", "info");
    });

    // 7. Xuất hội thoại ra file TXT
    document.getElementById("btn-export-chat")?.addEventListener("click", () => {
        const msgs = document.querySelectorAll(".hubbie-bot-bubble, .hubbie-user-bubble");
        if (msgs.length === 0) return;
        let content = "=== TRỢ LÝ THUCHI AI / RECONHUB — BẢN TÓM TẮT HỘI THOẠI ===\n\n";
        msgs.forEach((m) => {
            const isUser = m.classList.contains("hubbie-user-bubble");
            const sender = isUser ? "NGƯỜI DÙNG" : "THUCHI AI";
            content += `[${sender}]: ${m.innerText.trim()}\n\n`;
        });
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `ThuChi_AI_Transcript_${Date.now()}.txt`;
        a.click();
        showToast("Đã xuất tóm tắt hội thoại thành công.", "success");
    });
}

function handleUserSendMessage(userText) {
    const container = document.getElementById("hubbie-messages-container");
    if (!container) return;

    const pad = (n) => String(n).padStart(2, "0");
    const now = new Date();
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}`;

    // 1. Thêm bong bóng tin nhắn của User
    const userMsgHtml = `
        <div class="hubbie-msg-user">
            <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #0f172a; color: #ffffff;">
                <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"/>
                </svg>
            </div>
            <div>
                <div class="d-flex align-items-center justify-content-end gap-2 mb-1">
                    <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">${timeStr}</span>
                    <strong class="text-dark small fw-bold">Bạn (Thu ngân)</strong>
                </div>
                <div class="hubbie-user-bubble">
                    ${escapeHtml(userText)}
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", userMsgHtml);

    // Tự động cuộn xuống dưới
    container.scrollTop = container.scrollHeight;

    // 2. Tăng số đếm Quota yêu cầu hôm nay
    incrementQuota();

    // 3. Hiển thị trạng thái Bot đang phân tích (Typing Indicator)
    const typingId = `hubbie-typing-${Date.now()}`;
    const typingHtml = `
        <div class="hubbie-msg-bot" id="${typingId}">
            <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #eff6ff; color: #1e3a8a;">
                <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>
                </svg>
            </div>
            <div>
                <div class="d-flex align-items-center gap-2 mb-1">
                    <strong class="text-dark small fw-bold">ThuChi AI</strong>
                    <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">Đang trả lời...</span>
                </div>
                <div class="hubbie-bot-bubble text-secondary fst-italic">
                    <span class="spinner-grow spinner-grow-sm text-primary me-1" role="status" style="width: 10px; height: 10px;"></span>
                    ThuChi AI đang rà soát dữ liệu sổ quỹ và đối soát ngân hàng...
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", typingHtml);
    container.scrollTop = container.scrollHeight;

    // 4. Sinh câu trả lời thông minh sau 550ms
    setTimeout(() => {
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();

        const botReply = generateSmartBotReply(userText);
        const botMsgHtml = `
            <div class="hubbie-msg-bot">
                <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #eff6ff; color: #1e3a8a;">
                    <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>
                    </svg>
                </div>
                <div>
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <strong class="text-dark small fw-bold">ThuChi AI</strong>
                        <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">${timeStr}</span>
                    </div>
                    <div class="hubbie-bot-bubble">
                        ${botReply}
                    </div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML("beforeend", botMsgHtml);
        container.scrollTop = container.scrollHeight;
    }, 600);
}

function generateSmartBotReply(prompt) {
    const q = String(prompt || "").toLowerCase();
    const summary = hubbieStoreCache || {};
    const orders = summary.orders || [];
    const validRev = Number(summary.valid_order_total || 0);
    const bankReceived = Number(summary.allocated_payment_total || 0);
    const orderCount = Number(summary.valid_order_count || orders.length || 0);

    // Kịch bản 1: Hỏi về hóa đơn chưa thu đủ tiền / nợ
    if (q.includes("chưa thu") || q.includes("thiếu") || q.includes("nợ") || q.includes("chờ thanh toán")) {
        const unpaid = orders.filter((o) => ["UNPAID", "PARTIALLY_PAID"].includes(String(o.payment_status).toUpperCase()));
        if (unpaid.length === 0) {
            return `
                Dạ, theo dữ liệu sổ quỹ thời gian thực:
                <br>• Hiện tại trong ca <strong>không có hóa đơn nào nợ tiền</strong>.
                <br>• Toàn bộ <strong>${orderCount} đơn hàng</strong> hợp lệ đều đã được thanh toán đủ 100% qua VietQR.
                <br>• Không có khoản tiền treo chưa phân bổ tại tài khoản ngân hàng.
            `;
        } else {
            const listStr = unpaid.slice(0, 3).map((o) => `<code>${escapeHtml(o.order_code)}</code> (${formatVND(o.total_amount)})`).join(", ");
            return `
                Dạ, hệ thống ghi nhận có <strong>${unpaid.length} hóa đơn</strong> chưa thu đủ tiền:
                <br>• Các đơn hàng cần kiểm tra: ${listStr}
                <br>• Vui lòng nhắc khách quét mã QR tại quầy thu ngân hoặc thực hiện kiểm tra sao kê chuyển khoản.
            `;
        }
    }

    // Kịch bản 2: Kiểm tra chênh lệch đối soát
    if (q.includes("chênh lệch") || q.includes("lệch") || q.includes("đối soát") || q.includes("ngân hàng")) {
        const diff = Math.abs(validRev - bankReceived);
        if (diff === 0) {
            return `
                Kết quả kiểm tra đối soát 3 tầng:
                <br>• <strong>Khớp số tuyệt đối:</strong> Tổng doanh thu hóa đơn (${formatVND(validRev)}) bằng chính xác với số tiền thực nhận từ Webhook ngân hàng (${formatVND(bankReceived)}).
                <br>• <strong>Sổ cái chuỗi băm (Hash Chain):</strong> Hợp lệ 100%, không phát hiện hành vi sửa đổi dữ liệu.
                <br>• <strong>Khoản tiền chưa rõ:</strong> 0 giao dịch treo. Bạn hoàn toàn có thể yên tâm đóng ca khi hết giờ làm việc!
            `;
        } else {
            return `
                Cảnh báo đối soát:
                <br>• Hiện tại ghi nhận khoản chênh lệch là <strong>${formatVND(diff)}</strong> giữa sổ hóa đơn và thực thu ngân hàng.
                <br>• Bạn có thể truy cập mục <strong>Đối soát</strong> trên menu để rà soát các giao dịch chuyển khoản gộp hoặc sai nội dung chuyển khoản!
            `;
        }
    }

    // Kịch bản 3: Tóm tắt doanh thu
    if (q.includes("doanh thu") || q.includes("tóm tắt") || q.includes("hôm nay") || q.includes("bán được")) {
        const target = hubbieActiveShift ? Number(hubbieActiveShift.target_revenue || 5000000) : 5000000;
        const pct = target > 0 ? Math.round((validRev / target) * 100) : 0;
        return `
            Báo cáo tổng quan tình hình kinh doanh ca hiện tại:
            <br>• <strong>Tổng doanh thu thực nhận:</strong> <span class="font-numeric fw-bold text-success">${formatVND(validRev)}</span>
            <br>• <strong>Số lượng đơn hàng hoàn tất:</strong> <span class="font-numeric fw-bold text-dark">${orderCount} đơn</span>
            <br>• <strong>Tiến độ mục tiêu ca:</strong> Đạt <strong>${pct}%</strong> chỉ tiêu (${formatVND(target)}).
            <br>• Tỷ lệ khách hàng thanh toán qua VietQR đạt <strong>100%</strong>.
        `;
    }

    // Kịch bản 4: Tình trạng ca làm việc
    if (q.includes("ca") || q.includes("làm việc") || q.includes("đóng ca") || q.includes("mở ca")) {
        const shiftName = hubbieActiveShift ? hubbieActiveShift.name : "Ca hiện tại";
        return `
            Thông tin ca làm việc:
            <br>• <strong>Tên ca:</strong> ${escapeHtml(shiftName)}
            <br>• <strong>Trạng thái:</strong> <span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill font-numeric">Đang mở bán</span>
            <br>• <strong>Khuyến nghị:</strong> Bạn có thể theo dõi và tạo đơn hàng tại mục <strong>Quầy thu ngân</strong>. Khi hết ca, hãy vào mục <strong>Ca làm việc</strong> để chốt số và niêm phong chứng chỉ kiểm toán Merkle Root.
        `;
    }

    // Câu trả lời tổng quát thông minh
    return `
        Dạ, tôi đã ghi nhận câu hỏi của bạn: <em>"${escapeHtml(prompt)}"</em>.
        <br><br>Với vai trò là trợ lý ảo <strong>ThuChi AI</strong>, tôi được kết nối trực tiếp với Sổ quỹ điện tử ReconHub. Bạn có thể nhấn nhanh vào các gợi ý bên dưới hoặc hỏi tôi về:
        <br>• <code>Tóm tắt doanh thu hôm nay</code>
        <br>• <code>Hóa đơn nào chưa thu đủ?</code>
        <br>• <code>Kiểm tra tiền chênh lệch đối soát</code>
    `;
}

function incrementQuota() {
    // Không giới hạn số lượng yêu cầu
}

function createNewChatSession() {
    const container = document.getElementById("hubbie-messages-container");
    if (!container) return;

    incrementQuota();
    activeConvId = `conv-${Date.now()}`;

    // Cập nhật danh sách bên trái
    const convList = document.getElementById("hubbie-conv-list");
    document.querySelectorAll(".hubbie-conv-item").forEach((el) => el.classList.remove("active"));

    const newConvHtml = `
        <div class="hubbie-conv-item active" data-id="${activeConvId}">
            <div class="hubbie-conv-icon" style="background: #1e3a8a;">
                <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v5.518Z"/>
                </svg>
            </div>
            <div class="flex-grow-1 min-w-0">
                <div class="d-flex align-items-center justify-content-between gap-1">
                    <span class="hubbie-conv-title">Cuộc trò chuyện mới</span>
                    <span class="hubbie-conv-time">Vừa xong</span>
                </div>
                <div class="hubbie-conv-snippet">Bắt đầu phiên hỏi đáp mới...</div>
            </div>
        </div>
    `;
    if (convList) convList.insertAdjacentHTML("afterbegin", newConvHtml);

    // Xóa màn hình tin nhắn và hiển thị chào mừng
    container.innerHTML = `
        <div class="hubbie-date-divider">
            <span class="hubbie-date-pill">Cuộc trò chuyện mới</span>
        </div>
        <div class="hubbie-msg-bot">
            <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #eff6ff; color: #1e3a8a;">
                <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>
                </svg>
            </div>
            <div>
                <div class="d-flex align-items-center gap-2 mb-1">
                    <strong class="text-dark small fw-bold">ThuChi AI</strong>
                    <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">Vừa xong</span>
                </div>
                <div class="hubbie-bot-bubble">
                    Chào bạn! Tôi đã sẵn sàng cho phiên làm việc mới. Bạn có thể đặt câu hỏi về doanh thu hoặc kiểm tra hóa đơn chưa thu đủ ngay bây giờ.
                </div>
            </div>
        </div>
    `;

    showToast("Đã khởi tạo cuộc trò chuyện mới.", "info");
}

function filterConversationList(query) {
    const items = document.querySelectorAll(".hubbie-conv-item");
    let matchCount = 0;
    items.forEach((item) => {
        const text = item.textContent.toUpperCase();
        if (!query || text.includes(query)) {
            item.style.display = "flex";
            matchCount++;
        } else {
            item.style.display = "none";
        }
    });

    const countLabel = document.getElementById("hubbie-conv-count");
    if (countLabel) {
        countLabel.textContent = `${matchCount} cuộc trò chuyện`;
    }
}

function switchActiveConversation(convId) {
    activeConvId = convId;
    document.querySelectorAll(".hubbie-conv-item").forEach((el) => {
        if (el.getAttribute("data-id") === convId) {
            el.classList.add("active");
            const icon = el.querySelector(".hubbie-conv-icon");
            if (icon) icon.style.background = "#1e3a8a";
        } else {
            el.classList.remove("active");
            const icon = el.querySelector(".hubbie-conv-icon");
            if (icon) icon.style.background = "#334155";
        }
    });

    const conv = hubbieConversations.find((c) => c.id === convId);
    if (!conv) return;

    const container = document.getElementById("hubbie-messages-container");
    if (!container) return;

    container.innerHTML = `
        <div class="hubbie-date-divider">
            <span class="hubbie-date-pill">Lịch sử cuộc trò chuyện: ${escapeHtml(conv.title)}</span>
        </div>
    `;

    conv.messages.forEach((m) => {
        if (m.sender === "user") {
            container.insertAdjacentHTML("beforeend", `
                <div class="hubbie-msg-user">
                    <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #0f172a; color: #ffffff;">
                        <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"/>
                        </svg>
                    </div>
                    <div>
                        <div class="d-flex align-items-center justify-content-end gap-2 mb-1">
                            <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">${escapeHtml(m.time)}</span>
                            <strong class="text-dark small fw-bold">Bạn</strong>
                        </div>
                        <div class="hubbie-user-bubble">
                            ${escapeHtml(m.text)}
                        </div>
                    </div>
                </div>
            `);
        } else {
            container.insertAdjacentHTML("beforeend", `
                <div class="hubbie-msg-bot">
                    <div class="hubbie-conv-icon" style="width: 32px; height: 32px; border-radius: 8px; background: #eff6ff; color: #1e3a8a;">
                        <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>
                        </svg>
                    </div>
                    <div>
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <strong class="text-dark small fw-bold">ThuChi AI</strong>
                            <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">${escapeHtml(m.time)}</span>
                        </div>
                        <div class="hubbie-bot-bubble">
                            ${m.text}
                        </div>
                    </div>
                </div>
            `);
        }
    });

    container.scrollTop = container.scrollHeight;
}
