import os

# 1. Update frontend/pos.html
with open("frontend/pos.html", "r", encoding="utf-8") as f:
    pos_html = f.read()

pos_html_norm = pos_html.replace("\r\n", "\n")

target_pos_card = """                    <!-- Khối 2: Loa báo tiền vào tại quầy -->
                    <section class="recon-workspace-card" data-gsap="card">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <div class="d-flex align-items-center gap-2">
                                <span class="fp-brand-mark" style="width:30px;height:30px;background:#059669;">
                                    <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" aria-hidden="true">
                                        <path d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                                    </svg>
                                </span>
                                <h2 class="h6 fw-bold mb-0">Loa Báo Nhận Tiền</h2>
                            </div>
                            <div class="form-check form-switch mb-0">
                                <input class="form-check-input" type="checkbox" id="tts-enable-toggle" checked aria-label="Bật loa thông báo">
                            </div>
                        </div>

                        <div class="p-2 px-3 rounded-3 bg-light border mb-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-secondary" style="font-size: 0.72rem;">Thông báo gần nhất</span>
                                <span class="text-secondary" style="font-size: 0.7rem;" id="tts-last-time">Đang bật</span>
                            </div>
                            <div id="tts-last-message" class="small text-dark fw-medium mt-1" style="font-size: 0.8rem;">
                                Loa thu ngân đang hoạt động.
                            </div>
                        </div>

                        <div class="d-flex gap-1">
                            <button type="button" class="btn btn-sm btn-light border flex-fill" style="font-size: 0.74rem;" id="btn-test-tts-paid">
                                🔊 Đủ tiền
                            </button>
                            <button type="button" class="btn btn-sm btn-light border flex-fill" style="font-size: 0.74rem;" id="btn-test-tts-partial">
                                🔊 Thiếu tiền
                            </button>
                            <button type="button" class="btn btn-sm btn-light border flex-fill" style="font-size: 0.74rem;" id="btn-test-tts-overpaid">
                                🔊 Dư tiền
                            </button>
                        </div>
                    </section>"""

replacement_pos_card = """                    <!-- Khối 2: Loa báo tiền vào tại quầy (chỉ có bật/tắt, tự động phát khi thanh toán thành công) -->
                    <section class="recon-workspace-card" data-gsap="card">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <div class="d-flex align-items-center gap-2">
                                <span class="fp-brand-mark" style="width:30px;height:30px;background:#059669;">
                                    <svg class="hi-icon hi-icon-sm" viewBox="0 0 24 24" aria-hidden="true">
                                        <path d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                                    </svg>
                                </span>
                                <div>
                                    <h2 class="h6 fw-bold mb-0">Loa Báo Nhận Tiền</h2>
                                    <span class="text-secondary" style="font-size: 0.72rem;">Tự động phát khi nhận thanh toán</span>
                                </div>
                            </div>
                            <div class="form-check form-switch mb-0">
                                <input class="form-check-input" type="checkbox" id="tts-enable-toggle" checked aria-label="Bật/Tắt loa thông báo">
                            </div>
                        </div>

                        <div class="p-2 px-3 rounded-3 bg-light border">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-secondary" style="font-size: 0.72rem;">Thông báo gần nhất</span>
                                <span class="text-secondary font-numeric" style="font-size: 0.7rem;" id="tts-last-time">Đang bật</span>
                            </div>
                            <div id="tts-last-message" class="small text-dark fw-medium mt-1" style="font-size: 0.8rem;">
                                Loa đang hoạt động. Sẽ tự động đọc thông báo khi nhận tiền thành công.
                            </div>
                        </div>
                    </section>"""

assert target_pos_card in pos_html_norm, "Target pos card not found"
pos_html_norm = pos_html_norm.replace(target_pos_card, replacement_pos_card)

if "\r\n" in pos_html:
    pos_html_norm = pos_html_norm.replace("\n", "\r\n")

with open("frontend/pos.html", "w", encoding="utf-8") as f:
    f.write(pos_html_norm)
print("SUCCESS: frontend/pos.html updated")


# 2. Update frontend/js/tts_speaker.js
new_tts_speaker_js = """// ==========================================================================
// [P1-13] VIETQR RECONHUB — WEB SPEECH API TTS SPEAKER MODULE
// File: frontend/js/tts_speaker.js
// Chức năng: Loa thông báo tự động khi nhận tiền thanh toán thành công
// Quy tắc:
//   1. Nội dung phát theo số tiền nhận được (đủ tiền, chuyển thiếu, chuyển thừa).
//   2. Lưu trạng thái lastAnnouncedState[order_code] để chống đọc lặp khi Polling.
//   3. Hỗ trợ bật/tắt loa trực tiếp qua công tắc tts-enable-toggle.
// ==========================================================================

const lastAnnouncedState = {};
const orderPreviousPaid = {};
let cachedVietVoice = null;

// --------------------------------------------------------------------------
// 1. KHỞI TẠO & CHỌN GIỌNG ĐỌC TIẾNG VIỆT (vi-VN) TRÊN TRÌNH DUYỆT
// --------------------------------------------------------------------------
function initTtsVoices() {
    if (!("speechSynthesis" in window)) return;

    const pickVoice = () => {
        const voices = window.speechSynthesis.getVoices() || [];
        cachedVietVoice =
            voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("vi")) ||
            voices.find((v) => v.name && v.name.toLowerCase().includes("viet")) ||
            null;
    };

    pickVoice();
    if (typeof window.speechSynthesis.onvoiceschanged !== "undefined") {
        window.speechSynthesis.onvoiceschanged = pickVoice;
    }
}

initTtsVoices();

function isTtsEnabled() {
    const toggle = document.getElementById("tts-enable-toggle");
    if (toggle) return Boolean(toggle.checked);
    return localStorage.getItem("recon_tts_enabled") !== "false";
}

// --------------------------------------------------------------------------
// 2. HÀM ĐỌC SỐ TIỀN SANG VĂN BẢN DỄ NGHE CHO WEB SPEECH API
// --------------------------------------------------------------------------
function formatAmountForSpeech(amount) {
    const num = Math.round(Number(amount || 0));
    return new Intl.NumberFormat("vi-VN").format(num);
}

// --------------------------------------------------------------------------
// 3. TẠO CÂU THÔNG BÁO PHÁT THEO SỐ TIỀN THỰC TẾ NHẬN ĐƯỢC
// --------------------------------------------------------------------------
function buildOrderSpeechMessage({
    orderCode,
    paymentStatus,
    totalAmount = 0,
    netPaidAmount = 0,
    overpaidAmount = 0,
    receivedAmount = null
}) {
    const code = String(orderCode || "ORD").trim();
    const status = String(paymentStatus || "").toUpperCase();
    const total = Number(totalAmount || 0);
    const paid = Number(netPaidAmount || 0);
    const extra = Number(overpaidAmount || 0);
    const remaining = Math.max(0, total - paid);

    // Xác định số tiền thực tế nhận được trong giao dịch
    const actualReceived = Number(
        receivedAmount !== null && receivedAmount !== undefined && Number(receivedAmount) > 0
            ? receivedAmount
            : (extra > 0 ? (total + extra) : (paid > 0 ? paid : total))
    );

    // Trường hợp 1: Chuyển thừa (status = PAID và extra > 0)
    if (status === "PAID" && extra > 0) {
        return `Đã nhận ${formatAmountForSpeech(actualReceived)} đồng cho đơn hàng ${code}. Đơn hàng đã thanh toán đủ, phát sinh tiền chuyển thừa ${formatAmountForSpeech(extra)} đồng.`;
    }

    // Trường hợp 2: Chuyển thiếu (status = PARTIALLY_PAID)
    if (status === "PARTIALLY_PAID") {
        return `Đã nhận ${formatAmountForSpeech(actualReceived)} đồng cho đơn hàng ${code}. Khách chuyển thiếu, còn thiếu ${formatAmountForSpeech(remaining)} đồng.`;
    }

    // Trường hợp 3: Thanh toán thành công đủ tiền (status = PAID)
    if (status === "PAID") {
        return `Đã nhận ${formatAmountForSpeech(actualReceived)} đồng cho đơn hàng ${code}. Đơn hàng đã thanh toán thành công.`;
    }

    return "";
}

// --------------------------------------------------------------------------
// 4. PHÁT LOA GIỌNG NÓI & CẬP NHẬT NHẬT KÝ TRÊN GIAO DIỆN POS
// --------------------------------------------------------------------------
function speakTextVi(message) {
    if (!message) return false;

    // Cập nhật hộp hiển thị câu thông báo vừa phát trên pos.html
    const msgEl = document.getElementById("tts-last-message");
    const timeEl = document.getElementById("tts-last-time");
    if (msgEl) {
        msgEl.dataset.hasSpoken = "true";
        msgEl.textContent = `“${message}”`;
        if (window.gsap && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            window.gsap.fromTo(msgEl, { autoAlpha: 0.35, y: 4 }, { autoAlpha: 1, y: 0, duration: 0.25 });
        }
    }
    if (timeEl) {
        timeEl.textContent = new Date().toLocaleTimeString("vi-VN", { hour12: false });
    }

    if (!isTtsEnabled()) {
        return false;
    }

    if (!("speechSynthesis" in window)) {
        if (typeof showToast === "function") {
            showToast(`Thông báo: ${message}`, "info");
        }
        return false;
    }

    try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.lang = "vi-VN";
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        if (cachedVietVoice) {
            utterance.voice = cachedVietVoice;
        }
        window.speechSynthesis.speak(utterance);
        return true;
    } catch (err) {
        console.warn("Web Speech API error:", err);
        return false;
    }
}

// --------------------------------------------------------------------------
// 5. TỰ ĐỘNG PHÁT LOA KHI CÓ THANH TOÁN (Chống đọc lặp khi Polling)
// --------------------------------------------------------------------------
function announceOrderChangeIfNeeded(orderObj, options = { isInitialSnapshot: false }) {
    if (!orderObj || !orderObj.order_code) return false;

    const orderCode = String(orderObj.order_code);
    const paymentStatus = String(orderObj.payment_status || "UNPAID").toUpperCase();
    const totalAmount = Number(orderObj.total_amount || 0);
    const netPaidAmount = Number(
        orderObj.net_paid_amount ??
        orderObj.allocated_amount ??
        (paymentStatus === "PAID" ? totalAmount : 0)
    );
    const overpaidAmount = Number(orderObj.overpaid_amount || orderObj.extra_unallocated_amount || 0);

    // Khóa trạng thái nhận diện: "${payment_status}_${net_paid_amount}" (kèm tiền thừa nếu có)
    const stateSignature =
        overpaidAmount > 0
            ? `${paymentStatus}_${netPaidAmount}_OVER_${overpaidAmount}`
            : `${paymentStatus}_${netPaidAmount}`;

    const previousSignature = lastAnnouncedState[orderCode];
    const prevPaid = orderPreviousPaid[orderCode] !== undefined ? orderPreviousPaid[orderCode] : 0;

    lastAnnouncedState[orderCode] = stateSignature;
    orderPreviousPaid[orderCode] = netPaidAmount;

    // Lần đầu tiên mới mở trang POS thì chỉ ghi nhận snapshot, không đọc loa loạt đơn cũ
    if (options.isInitialSnapshot && previousSignature === undefined) {
        return false;
    }

    // Nếu trạng thái và số tiền thực thu không đổi so với lần Polling trước -> Bỏ qua (Chống đọc lặp)
    if (previousSignature === stateSignature) {
        return false;
    }

    // Chỉ đọc loa khi chuyển sang PARTIALLY_PAID hoặc PAID
    if (paymentStatus !== "PARTIALLY_PAID" && paymentStatus !== "PAID") {
        return false;
    }

    // Xác định số tiền nhận được trong đợt thanh toán này
    let receivedAmount = null;
    if (orderObj.last_received_amount !== undefined && orderObj.last_received_amount !== null && Number(orderObj.last_received_amount) > 0) {
        receivedAmount = Number(orderObj.last_received_amount);
    } else if (netPaidAmount > prevPaid) {
        receivedAmount = (netPaidAmount - prevPaid) + overpaidAmount;
    } else {
        receivedAmount = netPaidAmount + overpaidAmount;
    }

    const speechText = buildOrderSpeechMessage({
        orderCode,
        paymentStatus,
        totalAmount,
        netPaidAmount,
        overpaidAmount,
        receivedAmount
    });

    if (speechText) {
        speakTextVi(speechText);
        if (typeof showToast === "function") {
            showToast(speechText, paymentStatus === "PAID" ? "success" : "warning");
        }
        return true;
    }
    return false;
}

// --------------------------------------------------------------------------
// 6. HÀM KIỂM THỬ CHƯƠNG TRÌNH (Programmatic Test Scenarios)
// --------------------------------------------------------------------------
function triggerDemoTtsScenario(scenarioType) {
    if (scenarioType === "PAID") {
        const msg = buildOrderSpeechMessage({
            orderCode: "ORD1025",
            paymentStatus: "PAID",
            totalAmount: 200000,
            netPaidAmount: 200000,
            overpaidAmount: 0,
            receivedAmount: 200000
        });
        speakTextVi(msg);
        if (typeof showToast === "function") showToast(msg, "success");
    } else if (scenarioType === "PARTIAL") {
        const msg = buildOrderSpeechMessage({
            orderCode: "ORD1025",
            paymentStatus: "PARTIALLY_PAID",
            totalAmount: 200000,
            netPaidAmount: 120000,
            overpaidAmount: 0,
            receivedAmount: 120000
        });
        speakTextVi(msg);
        if (typeof showToast === "function") showToast(msg, "warning");
    } else if (scenarioType === "OVERPAID") {
        const msg = buildOrderSpeechMessage({
            orderCode: "ORD1025",
            paymentStatus: "PAID",
            totalAmount: 200000,
            netPaidAmount: 200000,
            overpaidAmount: 20000,
            receivedAmount: 220000
        });
        speakTextVi(msg);
        if (typeof showToast === "function") showToast(msg, "info");
    }
}
"""

with open("frontend/js/tts_speaker.js", "w", encoding="utf-8") as f:
    f.write(new_tts_speaker_js)
print("SUCCESS: frontend/js/tts_speaker.js updated")


# 3. Update frontend/js/pos.js
with open("frontend/js/pos.js", "r", encoding="utf-8") as f:
    pos_js = f.read()

pos_js_norm = pos_js.replace("\r\n", "\n")

target_pos_js = """    const ttsToggle = document.getElementById("tts-enable-toggle");
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
    document.getElementById("btn-test-tts-overpaid")?.addEventListener("click", () => triggerDemoTtsScenario("OVERPAID"));"""

replacement_pos_js = """    const ttsToggle = document.getElementById("tts-enable-toggle");
    if (ttsToggle) {
        const saved = localStorage.getItem("recon_tts_enabled");
        if (saved !== null) ttsToggle.checked = saved !== "false";

        const updateTtsUi = (enabled) => {
            const timeEl = document.getElementById("tts-last-time");
            const msgEl = document.getElementById("tts-last-message");
            if (timeEl && (!msgEl?.dataset?.hasSpoken)) {
                timeEl.textContent = enabled ? "Đang bật" : "Đã tắt";
            }
            if (!enabled && msgEl && (!msgEl?.dataset?.hasSpoken)) {
                msgEl.textContent = "Loa đã tắt. Hệ thống vẫn ghi nhận thanh toán bình thường.";
            } else if (enabled && msgEl && (!msgEl?.dataset?.hasSpoken)) {
                msgEl.textContent = "Loa đang hoạt động. Sẽ tự động đọc thông báo khi nhận tiền thành công.";
            }
        };
        updateTtsUi(ttsToggle.checked);

        ttsToggle.addEventListener("change", (e) => {
            localStorage.setItem("recon_tts_enabled", String(e.target.checked));
            updateTtsUi(e.target.checked);
            showToast(e.target.checked ? "Đã bật loa báo nhận tiền." : "Đã tắt loa báo nhận tiền.", "info");
        });
    }

    // Tự động kiểm tra cập nhật ngay khi người dùng chuyển lại tab Quầy thu ngân
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            loadPosOrders(false, true);
        }
    });"""

assert target_pos_js in pos_js_norm, "Target pos js not found"
pos_js_norm = pos_js_norm.replace(target_pos_js, replacement_pos_js)

if "\r\n" in pos_js:
    pos_js_norm = pos_js_norm.replace("\n", "\r\n")

with open("frontend/js/pos.js", "w", encoding="utf-8") as f:
    f.write(pos_js_norm)
print("SUCCESS: frontend/js/pos.js updated")
