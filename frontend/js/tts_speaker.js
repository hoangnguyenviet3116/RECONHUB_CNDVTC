// ==========================================================================
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
        return `Đã nhận ${formatAmountForSpeech(actualReceived)} đồng. Thừa ${formatAmountForSpeech(extra)} đồng.`;
    }

    // Trường hợp 2: Chuyển thiếu (status = PARTIALLY_PAID)
    if (status === "PARTIALLY_PAID") {
        return `Đã nhận ${formatAmountForSpeech(actualReceived)} đồng. Còn thiếu ${formatAmountForSpeech(remaining)} đồng.`;
    }

    // Trường hợp 3: Thanh toán thành công đủ tiền (status = PAID)
    if (status === "PAID") {
        return `Đã nhận ${formatAmountForSpeech(actualReceived)} đồng.`;
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
