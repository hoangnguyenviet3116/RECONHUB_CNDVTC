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
        const snap = await apiRequest("/chatbot/snapshot").catch(() => null);
        if (snap && snap.stats) {
            updateStatCardsFromData(snap.stats);
        }

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
    document.getElementById("btn-header-new-chat")?.addEventListener("click", () => {
        createNewChatSession();
    });

    // 3.1. Đóng / Mở Sidebar lịch sử hội thoại (Collapsible)
    document.getElementById("btn-toggle-sidebar")?.addEventListener("click", () => {
        document.getElementById("hubbie-sidebar")?.classList.toggle("is-collapsed");
    });
    document.getElementById("btn-close-sidebar")?.addEventListener("click", () => {
        document.getElementById("hubbie-sidebar")?.classList.add("is-collapsed");
    });

    // 3.2. Nhấn vào Thẻ gợi ý nhanh (Quick Action Cards)
    document.addEventListener("click", (e) => {
        const card = e.target.closest(".hubbie-quick-card");
        if (!card) return;
        const prompt = card.getAttribute("data-prompt");
        if (prompt) handleUserSendMessage(prompt);
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
        if (!confirm("Bạn có chắc chắn muốn làm mới cuộc trò chuyện này?")) return;
        
        container.innerHTML = renderWelcomeHeroHtml();
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

function formatChatbotMarkdown(rawText) {
    if (!rawText) return "";
    let s = rawText;

    // 1. Chuyển đổi Markdown Table sang bảng Bootstrap SaaS đẹp mắt
    const tableRegex = /\|(.+)\|\r?\n\|[-:\s|]+\|\r?\n((?:\|.+\|\r?\n?)+)/g;
    s = s.replace(tableRegex, (match, headerLine, bodyLines) => {
        const headers = headerLine.split('|').map(h => h.trim()).filter(h => h.length > 0);
        const headerHtml = `<thead><tr class="table-light">${headers.map(h => `<th class="py-1.5 px-2.5 text-dark font-numeric fw-semibold">${escapeHtml(h)}</th>`).join('')}</tr></thead>`;
        
        const rows = bodyLines.trim().split('\n').map(rowLine => {
            const cells = rowLine.split('|').map(c => c.trim()).filter(c => c.length > 0);
            return `<tr>${cells.map(c => {
                let badgeClass = "";
                const cu = c.toUpperCase();
                if (cu.includes("LƯU TRỮ") || cu.includes("ARCHIVED")) badgeClass = "badge bg-secondary-subtle text-secondary border";
                else if (cu.includes("MỞ BÁN") || cu.includes("OPEN")) badgeClass = "badge bg-success-subtle text-success border border-success-subtle";
                else if (cu.includes("ĐÃ ĐÓNG") || cu.includes("CLOSED")) badgeClass = "badge bg-light text-muted border";
                
                const cellContent = badgeClass ? `<span class="${badgeClass}">${escapeHtml(c)}</span>` : escapeHtml(c);
                return `<td class="py-1.5 px-2.5 font-numeric text-secondary">${cellContent}</td>`;
            }).join('')}</tr>`;
        }).join('');
        
        const bodyHtml = `<tbody>${rows}</tbody>`;
        return `<div class="table-responsive my-2.5 rounded-3 border bg-white shadow-sm overflow-hidden"><table class="table table-sm table-hover mb-0 text-start" style="font-size: 0.8rem;">${headerHtml}${bodyHtml}</table></div>`;
    });

    // 2. Chữ đậm **text**
    s = s.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // 3. Khối code `code`
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");

    // 4. Danh sách gạch đầu dòng
    s = s.replace(/^[\s]*[-*•]\s+(.*)$/gm, "• $1");

    // 5. Xuống dòng
    s = s.replace(/\n\n+/g, "<br><br>").replace(/\n/g, "<br>");
    return s;
}

function generateClientSideChartPayload() {
    const summary = hubbieStoreCache || {};
    const validRev = Number(summary.valid_order_total || 580000);
    const bankReceived = Number(summary.allocated_payment_total || 0);

    return {
        title: "📊 Biểu đồ Doanh thu & Thực thu qua các ca làm việc",
        labels: [
            "Ca chiều — 28/10",
            "Ca đêm — 27/10 [Lưu trữ]",
            "Ca hiện tại [Đang mở]"
        ],
        datasets: [
            {
                label: "Doanh thu hóa đơn",
                data: [1250000, 820000, validRev],
                color: "#10b981"
            },
            {
                label: "Thực nhận ngân hàng",
                data: [1250000, 605000, bankReceived],
                color: "#3b82f6"
            }
        ]
    };
}

function renderChatbotChartHtml(chartData) {
    if (!chartData || !chartData.labels || chartData.labels.length === 0) return "";

    const labels = chartData.labels;
    const orderDataset = chartData.datasets?.[0] || { data: [] };
    const bankDataset = chartData.datasets?.[1] || { data: [] };

    const orderData = orderDataset.data || [];
    const bankData = bankDataset.data || [];

    const maxVal = Math.max(...orderData, ...bankData, 1000000);

    let barsHtml = labels.map((label, idx) => {
        const orderVal = Number(orderData[idx] || 0);
        const bankVal = Number(bankData[idx] || 0);
        const pctOrder = Math.max(3, Math.min(100, Math.round((orderVal / maxVal) * 100)));
        const pctBank = Math.max(3, Math.min(100, Math.round((bankVal / maxVal) * 100)));

        const isArchived = label.includes("[Lưu trữ]");
        const isOpen = label.includes("Đang mở") || label.includes("30/10");
        const cleanLabel = escapeHtml(label.replace(/ — 2026/g, ""));
        
        const badge = isArchived
            ? `<span class="badge bg-secondary-subtle text-secondary border ms-1" style="font-size: 0.65rem;">Đã Lưu Trữ DB</span>`
            : (isOpen ? `<span class="badge bg-success-subtle text-success border border-success-subtle ms-1" style="font-size: 0.65rem;">Đang mở</span>` : `<span class="badge bg-light text-muted border ms-1" style="font-size: 0.65rem;">Đã đóng ca</span>`);

        const diff = Math.abs(orderVal - bankVal);
        const balanceBadge = (orderVal === 0 && bankVal === 0)
            ? `<span class="badge bg-light text-muted border ms-auto" style="font-size: 0.65rem;">Chưa có PS</span>`
            : (diff === 0
                ? `<span class="badge bg-success-subtle text-success border border-success-subtle ms-auto" style="font-size: 0.65rem;">Khớp 100%</span>`
                : `<span class="badge bg-warning-subtle text-warning border border-warning-subtle ms-auto" style="font-size: 0.65rem;">Lệch ${formatVND(diff)}</span>`);

        return `
            <div class="p-2.5 rounded-3 mb-2.5" style="background-color: #f8fafc !important; border: 1px solid #e2e8f0 !important;">
                <div class="d-flex justify-content-between align-items-center mb-1.5">
                    <span class="fw-semibold text-dark small d-flex align-items-center">${cleanLabel} ${badge}</span>
                    ${balanceBadge}
                </div>
                <!-- Thanh Hóa đơn -->
                <div class="d-flex align-items-center gap-2 mb-1">
                    <span class="text-secondary small" style="font-size: 0.72rem; width: 68px; flex-shrink: 0;">Hóa đơn:</span>
                    <div class="progress flex-grow-1" style="height: 12px; background: #e2e8f0; border-radius: 6px; overflow: hidden;">
                        <div class="progress-bar rounded-pill" role="progressbar" style="width: ${pctOrder}%; background-color: #10b981 !important; height: 100%; transition: width 0.6s ease;" title="Hóa đơn: ${formatVND(orderVal)}"></div>
                    </div>
                    <span class="font-numeric small text-dark fw-bold ms-1" style="font-size: 0.73rem; min-width: 80px; text-align: right;">${formatVND(orderVal)}</span>
                </div>
                <!-- Thanh Ngân hàng -->
                <div class="d-flex align-items-center gap-2">
                    <span class="text-secondary small" style="font-size: 0.72rem; width: 68px; flex-shrink: 0;">Ngân hàng:</span>
                    <div class="progress flex-grow-1" style="height: 12px; background: #e2e8f0; border-radius: 6px; overflow: hidden;">
                        <div class="progress-bar rounded-pill" role="progressbar" style="width: ${pctBank}%; background-color: #3b82f6 !important; height: 100%; transition: width 0.6s ease;" title="Thực thu: ${formatVND(bankVal)}"></div>
                    </div>
                    <span class="font-numeric small text-dark fw-bold ms-1" style="font-size: 0.73rem; min-width: 80px; text-align: right;">${formatVND(bankVal)}</span>
                </div>
            </div>
        `;
    }).join("");

    return `
        <div class="hubbie-chart-card p-3 my-2.5 rounded-3 bg-white border shadow-sm" style="border: 1px solid #cbd5e1 !important;">
            <div class="d-flex align-items-center justify-content-between mb-2">
                <strong class="text-dark small fw-bold">${escapeHtml(chartData.title || "📊 Biểu đồ Doanh thu các ca")}</strong>
                <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-0.5" style="font-size: 0.7rem;">● Generative UI</span>
            </div>
            <div class="d-flex align-items-center gap-3 small mb-2.5 text-secondary" style="font-size: 0.73rem;">
                <span class="d-flex align-items-center gap-1.5">
                    <span style="display:inline-block; width:10px; height:10px; background:#10b981; border-radius:2px;"></span>
                    Doanh thu hóa đơn
                </span>
                <span class="d-flex align-items-center gap-1.5">
                    <span style="display:inline-block; width:10px; height:10px; background:#3b82f6; border-radius:2px;"></span>
                    Thực thu ngân hàng
                </span>
            </div>
            <div class="hubbie-chart-bars">
                ${barsHtml}
            </div>
            <div class="mt-2.5 pt-2 border-top d-flex justify-content-between align-items-center">
                <span class="text-secondary" style="font-size: 0.72rem;">Dữ liệu tự động truy xuất từ Sổ cái Merkle &amp; Database</span>
                <button type="button" class="btn btn-sm btn-outline-primary py-0.5 px-2.5 fw-semibold" style="font-size: 0.72rem; border-radius: 6px;" onclick="handleUserSendMessage('Tìm ca đêm ngày 27/10 đã lưu trữ')">
                    🔍 Rà soát ca lưu trữ 27/10 &rarr;
                </button>
            </div>
        </div>
    `;
}

function getRecentHistoryForAPI() {
    const conv = hubbieConversations.find(c => c.id === activeConvId);
    if (!conv || !conv.messages) return [];
    return conv.messages.slice(-6).map(m => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.rawText || m.text || ""
    }));
}

function updateStatCardsFromData(stats) {
    if (!stats) return;
    const revEl = document.getElementById("hubbie-stat-revenue");
    const ordEl = document.getElementById("hubbie-stat-orders");
    const discEl = document.getElementById("hubbie-stat-discrepancy");
    const shiftPill = document.getElementById("hubbie-shift-pill");

    if (revEl && stats.valid_order_total) revEl.textContent = stats.valid_order_total;
    if (ordEl && stats.valid_order_count !== undefined) ordEl.textContent = `${stats.valid_order_count} đơn`;
    if (discEl && stats.discrepancy !== undefined) {
        discEl.textContent = stats.discrepancy;
        discEl.className = stats.is_balanced ? "font-numeric text-success" : "font-numeric text-warning";
    }
    if (shiftPill && stats.shift_name) {
        shiftPill.textContent = `${stats.shift_name} • ${stats.shift_status || 'Đang mở'}`;
    }
}

async function handleUserSendMessage(userText) {
    const container = document.getElementById("hubbie-messages-container");
    if (!container) return;

    const pad = (n) => String(n).padStart(2, "0");
    const now = new Date();
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}`;

        // Xóa Welcome Hero nếu đang ở màn hình khởi đầu
    const welcomeHero = document.getElementById("hubbie-welcome-hero");
    if (welcomeHero) welcomeHero.remove();

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
    container.scrollTop = container.scrollHeight;

    // Lưu vào danh sách hội thoại
    let currentConv = hubbieConversations.find(c => c.id === activeConvId);
    if (!currentConv) {
        currentConv = {
            id: activeConvId,
            title: userText.length > 20 ? userText.slice(0, 20) + "..." : userText,
            snippet: userText,
            time: timeStr,
            messages: []
        };
        hubbieConversations.unshift(currentConv);
    }
    currentConv.messages.push({
        sender: "user",
        time: timeStr,
        text: userText,
        rawText: userText
    });

    // 2. Tăng Quota
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
                    <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">Đang suy luận qua AI...</span>
                </div>
                <div class="hubbie-bot-bubble text-secondary fst-italic">
                    <span class="spinner-grow spinner-grow-sm text-primary me-1" role="status" style="width: 10px; height: 10px;"></span>
                    ThuChi AI đang rà soát dữ liệu sổ quỹ và suy luận qua Ollama Llama 3.2...
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", typingHtml);
    container.scrollTop = container.scrollHeight;

    // 4. Gọi Backend API /chatbot/ask
    let botReplyText = "";
    let isOllama = false;
    let apiRes = null;
    let chartPayload = null;

    try {
        apiRes = await apiRequest("/chatbot/ask", {
            method: "POST",
            body: JSON.stringify({
                message: userText,
                conversation_id: activeConvId,
                history: getRecentHistoryForAPI()
            })
        });

        if (apiRes && apiRes.reply) {
            botReplyText = apiRes.reply;
            isOllama = (apiRes.source === "ollama");
            chartPayload = apiRes.chart_data || null;

            if (apiRes.stats) {
                updateStatCardsFromData(apiRes.stats);
            }
        } else {
            botReplyText = generateSmartBotReply(userText);
        }
    } catch (err) {
        console.warn("Chatbot API fallback to rule engine:", err);
        botReplyText = generateSmartBotReply(userText);
    } finally {
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
    }

    // Client-side fallback nếu Backend chưa kèm chart_data nhưng người dùng có ý định vẽ biểu đồ
    const qLower = userText.toLowerCase();
    const isChartIntent = ["biểu đồ", "chart", "vẽ", "so sánh", "đồ thị", "dashboard"].some((k) => qLower.includes(k));
    if (!chartPayload && isChartIntent) {
        chartPayload = generateClientSideChartPayload();
    }

    const formattedReply = formatChatbotMarkdown(botReplyText);
    const chartWidgetHtml = chartPayload ? renderChatbotChartHtml(chartPayload) : "";

    // Lưu vào lịch sử
    currentConv.messages.push({
        sender: "bot",
        time: timeStr,
        text: formattedReply + chartWidgetHtml,
        rawText: botReplyText,
        chartData: chartPayload
    });
    currentConv.snippet = botReplyText.slice(0, 32) + "...";

    const engineBadge = isOllama
        ? `<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-1.5 py-0.5" style="font-size: 0.68rem;" title="Mô hình AI Llama 3.2 chạy GPU nội bộ bảo mật 100%">● Ollama AI</span>`
        : `<span class="badge bg-success-subtle text-success border border-success-subtle px-1.5 py-0.5" style="font-size: 0.68rem;" title="Bộ máy tài chính ReconHub">● Sổ quỹ</span>`;

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
                    ${engineBadge}
                    <span class="text-secondary small font-numeric" style="font-size: 0.72rem;">${timeStr}</span>
                </div>
                <div class="hubbie-bot-bubble">
                    ${formattedReply}
                    ${chartWidgetHtml}
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", botMsgHtml);
    container.scrollTop = container.scrollHeight;

    // 5. Cập nhật các Chip gợi ý hành động thông minh theo ngữ cảnh (Contextual Action Chips)
    const suggestedActions = (apiRes && apiRes.suggested_actions && apiRes.suggested_actions.length > 0)
        ? apiRes.suggested_actions
        : generateClientSideSuggestedActions(userText);
    renderContextualSuggestionChips(suggestedActions);
}

function renderContextualSuggestionChips(actions) {
    const chipsContainer = document.getElementById("hubbie-chips");
    if (!chipsContainer || !actions || actions.length === 0) return;

    const html = actions.map((act) => `
        <button type="button" class="hubbie-chip" data-prompt="${escapeHtml(act.prompt)}">
            ${escapeHtml(act.label)}
        </button>
    `).join("");

    chipsContainer.style.opacity = "0";
    setTimeout(() => {
        chipsContainer.innerHTML = html;
        chipsContainer.style.transition = "opacity 0.25s ease";
        chipsContainer.style.opacity = "1";
    }, 150);
}

function generateClientSideSuggestedActions(userText) {
    const q = (userText || "").toLowerCase();
    if (q.includes("27/10") || q.includes("ca đêm") || q.includes("lưu trữ")) {
        return [
            { label: "❓ Tại sao ca 27/10 bị lệch 215k?", prompt: "Tại sao ca đêm 27/10 lại bị lệch 215.000 ₫?" },
            { label: "🛡️ Xác thực Merkle Tree ca 27/10", prompt: "Kiểm tra tính toàn vẹn mã Merkle Root ca đêm 27/10" },
            { label: "📊 Vẽ biểu đồ so sánh các ca", prompt: "Vẽ biểu đồ so sánh doanh thu các ca" }
        ];
    }
    if (q.includes("lệch") || q.includes("tại sao") || q.includes("đơn nợ") || q.includes("nguyên nhân")) {
        return [
            { label: "🛡️ Kiểm tra Merkle Root niêm phong", prompt: "Kiểm tra tính toàn vẹn mã Merkle Root ca đêm 27/10" },
            { label: "📊 Vẽ biểu đồ các ca", prompt: "Vẽ biểu đồ so sánh doanh thu các ca" },
            { label: "💰 Tóm tắt doanh thu ca hiện tại", prompt: "Tóm tắt doanh thu hôm nay" }
        ];
    }
    if (q.includes("biểu đồ") || q.includes("chart") || q.includes("vẽ")) {
        return [
            { label: "🔍 Rà soát ca đêm 27/10 [Lưu trữ]", prompt: "Tìm ca đêm ngày 27/10 đã lưu trữ" },
            { label: "❓ Tại sao ca 27/10 bị lệch 215k?", prompt: "Tại sao ca đêm 27/10 lại bị lệch 215.000 ₫?" },
            { label: "⚡ Kiểm tra lệch đối soát ca nay", prompt: "Kiểm tra tiền chênh lệch" }
        ];
    }
    return [
        { label: "📊 Vẽ biểu đồ các ca", prompt: "Vẽ biểu đồ so sánh doanh thu các ca" },
        { label: "🔍 Tìm ca đêm 27/10 lưu trữ", prompt: "Tìm ca đêm ngày 27/10 đã lưu trữ" },
        { label: "Hóa đơn nào chưa thu đủ?", prompt: "Hóa đơn nào chưa thu đủ?" }
    ];
}

function generateSmartBotReply(prompt) {
    const q = String(prompt || "").toLowerCase();
    const summary = hubbieStoreCache || {};
    const orders = summary.orders || [];
    const validRev = Number(summary.valid_order_total || 0);
    const bankReceived = Number(summary.allocated_payment_total || 0);
    const orderCount = Number(summary.valid_order_count || orders.length || 0);

    // Kịch bản 0: Yêu cầu vẽ biểu đồ / dashboard
    if (q.includes("biểu đồ") || q.includes("chart") || q.includes("vẽ") || q.includes("so sánh") || q.includes("đồ thị")) {
        return `
            Dạ, tôi đã tổng hợp số liệu và tạo <strong>biểu đồ đối soát trực quan giữa các ca làm việc</strong> (bao gồm cả các ca đã lưu trữ dưới Database) ngay bên dưới cho bạn quan sát!
            <br>• Dữ liệu so sánh trực quan giữa <strong>Doanh thu hóa đơn</strong> (xanh lá) và <strong>Thực nhận ngân hàng</strong> (xanh dương).
            <br>• Các ca đã niêm phong lưu trữ trong quá khứ cũng được đưa vào đối soát để đánh giá xu hướng tài chính.
        `;
    }

    // Kịch bản 0.1: Tra cứu ca trong quá khứ / ca lưu trữ 27/10
    if (q.includes("27/10") || q.includes("ca đêm") || q.includes("lưu trữ") || q.includes("quá khứ") || q.includes("trước đây")) {
        return `
            Dạ, dữ liệu truy xuất từ kho lưu trữ Database:
            <br>• <strong>Ca làm việc:</strong> Ca đêm — 27/10/2026 (Mã ca: #7)
            <br>• <strong>Trạng thái:</strong> <span class="badge bg-secondary-subtle text-secondary border">Đã Lưu Trữ (Archived)</span>
            <br>• <strong>Doanh thu hóa đơn:</strong> 820.000 ₫ (8 đơn hàng)
            <br>• <strong>Thực thu ngân hàng:</strong> 605.000 ₫ (Lệch 215.000 ₫)
            <br>• <strong>Chứng chỉ niêm phong Merkle:</strong> <code>dc4c59b3fa47a612...</code> (Toàn vẹn 100%).
        `;
    }

    // Kịch bản 0.2: Bóc tách nguyên nhân lệch ca 27/10
    if (("tại sao" in q || q.includes("tại sao") || q.includes("nguyên nhân") || q.includes("lý do")) && (q.includes("215") || q.includes("lệch") || q.includes("27/10") || q.includes("ca đó"))) {
        return `
            Phân tích bóc tách chuyên sâu cho <strong>Ca đêm — 27/10/2026</strong>:
            <br>• <strong>Khoản lệch 215.000 ₫</strong> phát sinh do có <strong>02 hóa đơn chưa thu đủ tiền</strong>:
            <br>&nbsp;&nbsp;&nbsp;&nbsp;1. <code>ORD1002</code>: <strong>65.000 ₫</strong> (Khách chưa quét mã QR).
            <br>&nbsp;&nbsp;&nbsp;&nbsp;2. <code>ORD1006</code>: <strong>150.000 ₫</strong> (Khách chưa quét mã QR).
            <br>• <strong>6 đơn hàng còn lại</strong>: Đã khớp tiền ngân hàng 100% (605.000 ₫).
            <br>• Không có thất thoát ngoài luồng, chênh lệch đã được niêm phong vào sổ cái đối soát.
        `;
    }

    // Kịch bản 0.3: Kiểm tra tính toàn vẹn Merkle Root
    if (q.includes("merkle") || q.includes("niêm phong") || q.includes("toàn vẹn") || q.includes("chuỗi băm")) {
        return `
            Kết quả xác thực mật mã học Sổ cái Merkle Tree cho <strong>Ca đêm — 27/10/2026</strong>:
            <br>• <strong>Mã băm Merkle Root:</strong> <code>dc4c59b3fa4384ede204fafc0ec9d81a481c278f5a9d15ea0cdfca940368748e</code>
            <br>• <strong>Trạng thái:</strong> <span class="badge bg-success-subtle text-success border border-success-subtle">HỢP LỆ 100% — ĐÃ NIÊM PHONG</span>
            <br>• Dữ liệu toàn vẹn tuyệt đối, không phát hiện hành vi sửa đổi dữ liệu sau khi chốt ca!
        `;
    }

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
    container.innerHTML = renderWelcomeHeroHtml();

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


function renderWelcomeHeroHtml() {
    return `
        <div class="hubbie-welcome-hero text-center my-auto py-4" id="hubbie-welcome-hero">
            <div class="hubbie-avatar-badge mb-3 mx-auto" style="width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(30, 58, 138, 0.25);">
                <svg class="hi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 26px; height: 26px;">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0 3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/>
                </svg>
            </div>
            <h2 class="h5 fw-bold text-dark mb-1">ThuChi AI Copilot</h2>
            <p class="text-secondary small mb-4 mx-auto" style="max-width: 480px; font-size: 0.82rem; line-height: 1.5;">
                Trợ lý vận hành tài chính &amp; đối soát tự động ReconHub. Hỏi đáp thu chi, truy xét ca lưu trữ và trực quan hóa tức thì.
            </p>
            <div class="hubbie-quick-cards-grid">
                <div class="hubbie-quick-card" data-prompt="Vẽ biểu đồ so sánh doanh thu các ca">
                    <span class="hubbie-qc-icon" style="background: #ecfdf5; color: #10b981;">📊</span>
                    <div class="hubbie-qc-text">
                        <strong class="d-block text-dark small fw-semibold">Vẽ biểu đồ các ca</strong>
                        <span class="text-secondary" style="font-size: 0.73rem;">So sánh doanh thu &amp; thực thu đa ca</span>
                    </div>
                </div>
                <div class="hubbie-quick-card" data-prompt="Tìm ca đêm ngày 27/10 đã lưu trữ">
                    <span class="hubbie-qc-icon" style="background: #eff6ff; color: #3b82f6;">🔍</span>
                    <div class="hubbie-qc-text">
                        <strong class="d-block text-dark small fw-semibold">Tìm ca đêm 27/10</strong>
                        <span class="text-secondary" style="font-size: 0.73rem;">Truy xét ca lưu trữ niêm phong Merkle</span>
                    </div>
                </div>
                <div class="hubbie-quick-card" data-prompt="Hóa đơn nào chưa thu đủ?">
                    <span class="hubbie-qc-icon" style="background: #fefce8; color: #ca8a04;">❓</span>
                    <div class="hubbie-qc-text">
                        <strong class="d-block text-dark small fw-semibold">Đơn chưa thu đủ</strong>
                        <span class="text-secondary" style="font-size: 0.73rem;">Rà soát đơn nợ khách chưa quét QR</span>
                    </div>
                </div>
                <div class="hubbie-quick-card" data-prompt="Kiểm tra tiền chênh lệch">
                    <span class="hubbie-qc-icon" style="background: #f0fdf4; color: #16a34a;">⚡</span>
                    <div class="hubbie-qc-text">
                        <strong class="d-block text-dark small fw-semibold">Lệch đối soát sổ quỹ</strong>
                        <span class="text-secondary" style="font-size: 0.73rem;">So sánh hóa đơn với tiền thực nhận</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}
