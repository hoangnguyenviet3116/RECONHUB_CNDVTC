# 1. Update frontend/bank-simulator.html
with open("frontend/bank-simulator.html", "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")
target_html = """    <script src="js/api.js"></script>
    <script src="js/bank_simulator.js"></script>"""

replacement_html = """    <script src="js/api.js"></script>
    <script src="js/tts_speaker.js"></script>
    <script src="js/bank_simulator.js"></script>"""

assert target_html in content_norm, "Target html not found"
content_norm = content_norm.replace(target_html, replacement_html)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open("frontend/bank-simulator.html", "w", encoding="utf-8") as f:
    f.write(content_norm)
print("SUCCESS: frontend/bank-simulator.html updated")

# 2. Update frontend/js/bank_simulator.js
with open("frontend/js/bank_simulator.js", "r", encoding="utf-8") as f:
    sim_js = f.read()

sim_js_norm = sim_js.replace("\r\n", "\n")

target_sim_js = """        generateFreshReferenceCode();
        await loadBankTransactionsList(false);
        await loadOrdersForSimulatorSelect();"""

replacement_sim_js = """        generateFreshReferenceCode();
        await loadBankTransactionsList(false);
        await loadOrdersForSimulatorSelect();

        // Tự động phát âm thanh loa thông báo nếu tính năng loa đang bật
        if (typeof announceOrderChangeIfNeeded === "function" && typeof isTtsEnabled === "function" && isTtsEnabled()) {
            const match = transferContent.toUpperCase().match(/ORD[A-Z0-9_-]*/);
            if (match) {
                const targetCode = match[0];
                try {
                    const allOrders = await apiRequest("/orders");
                    const ord = Array.isArray(allOrders) ? allOrders.find(o => o.order_code === targetCode) : null;
                    if (ord && ["PAID", "PARTIALLY_PAID"].includes(String(ord.payment_status).toUpperCase())) {
                        announceOrderChangeIfNeeded(ord);
                    }
                } catch (_) {}
            }
        }"""

assert target_sim_js in sim_js_norm, "Target sim js not found"
sim_js_norm = sim_js_norm.replace(target_sim_js, replacement_sim_js)

if "\r\n" in sim_js:
    sim_js_norm = sim_js_norm.replace("\n", "\r\n")

with open("frontend/js/bank_simulator.js", "w", encoding="utf-8") as f:
    f.write(sim_js_norm)
print("SUCCESS: frontend/js/bank_simulator.js updated")
