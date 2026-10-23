// ==========================================================================
// [P1-13] VIETQR RECONHUB — WEB SPEECH API TTS SPEAKER MODULE
// File: frontend/js/tts_speaker.js
// Quy tắc bắt buộc (Nguyên tắc 8 - README & P1-13):
//   1. Tách riêng 3 mẫu câu thông báo cho PAID, PARTIALLY_PAID và Chuyển thừa.
//   2. Lưu trạng thái lastAnnouncedState[order_code] để chống đọc lặp khi Polling.
// ==========================================================================

const lastAnnouncedState = {};
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
// 3. TẠO 3 MẪU CÂU THÔNG BÁO CHUẨN NGHIỆP VỤ P1-13 (TC-02, TC-03, TC-04)
// --------------------------------------------------------------------------
function buildOrderSpeechMessage({
    orderCode,
    paymentStatus,
    totalAmount = 0,
    netPaidAmount = 0,
    overpaidAmount = 0
}) {
    const code = String(orderCode || "ORD").trim();
    const status = String(paymentStatus || "").toUpperCase();
    const total = Number(totalAmount || 0);
    const paid = Number(netPaidAmount || 0);
    const extra = Number(overpaidAmount || 0);
    const remaining = Math.max(0, total - paid);

    // Trường hợp 3 (TC-04): Phát sinh khoản tiền chuyển thừa (unallocated_amount > 0 từ giao dịch của đơn)
    if (status === "PAID" && extra > 0) {
        return `Đơn hàng ${code} đã thanh toán đủ, phát sinh khoản chuyển thừa ${formatAmountForSpeech(extra)} đồng cần kiểm tra.`;
    }

    // Trường hợp 1 (TC-02): Đơn hàng chuyển sang PAID (Thu đủ 100%, không có tiền thừa)
    if (status === "PAID") {
        const displayPaid = paid > 0 ? paid : total;
        return `ReconHub thông báo: Đơn hàng ${code} đã thanh toán đủ ${formatAmountForSpeech(displayPaid)} đồng.`;
    }

    // Trường hợp 2 (TC-03): Đơn hàng chuyển sang PARTIALLY_PAID (Khách chuyển thiếu)
    if (status === "PARTIALLY_PAID") {
        return `Chú ý: Đơn hàng ${code} mới nhận một phần là ${formatAmountForSpeech(paid)} đồng, còn thiếu ${formatAmountForSpeech(remaining)} đồng.`;
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
            showToast(`Thông báo TTS: ${message}`, "info");
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
// 5. KIỂM TRA CHỐNG ĐỌC LẶP KHI POLLING (lastAnnouncedState[order_code])
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

    // Khóa trạng thái chuẩn theo đặc tả P1-13: "${payment_status}_${net_paid_amount}" (kèm tiền thừa nếu có)
    const stateSignature =
        overpaidAmount > 0
            ? `${paymentStatus}_${netPaidAmount}_OVER_${overpaidAmount}`
            : `${paymentStatus}_${netPaidAmount}`;

    const previousSignature = lastAnnouncedState[orderCode];
    lastAnnouncedState[orderCode] = stateSignature;

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

    const speechText = buildOrderSpeechMessage({
        orderCode,
        paymentStatus,
        totalAmount,
        netPaidAmount,
        overpaidAmount
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
// 6. HÀM KIỂM THỬ NHANH 3 KỊCH BẢN LOA TTS TRÊN MÀN HÌNH POS (DEMO TRỰC TIẾP)
// --------------------------------------------------------------------------
function triggerDemoTtsScenario(scenarioType) {
    if (scenarioType === "PAID") {
        const msg = buildOrderSpeechMessage({
            orderCode: "ORD1025",
            paymentStatus: "PAID",
            totalAmount: 200000,
            netPaidAmount: 200000,
            overpaidAmount: 0
        });
        speakTextVi(msg);
        if (typeof showToast === "function") showToast(msg, "success");
    } else if (scenarioType === "PARTIAL") {
        const msg = buildOrderSpeechMessage({
            orderCode: "ORD1025",
            paymentStatus: "PARTIALLY_PAID",
            totalAmount: 200000,
            netPaidAmount: 120000,
            overpaidAmount: 0
        });
        speakTextVi(msg);
        if (typeof showToast === "function") showToast(msg, "warning");
    } else if (scenarioType === "OVERPAID") {
        const msg = buildOrderSpeechMessage({
            orderCode: "ORD1025",
            paymentStatus: "PAID",
            totalAmount: 200000,
            netPaidAmount: 200000,
            overpaidAmount: 20000
        });
        speakTextVi(msg);
        if (typeof showToast === "function") showToast(msg, "info");
    }
}