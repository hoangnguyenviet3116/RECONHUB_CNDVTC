# -*- coding: utf-8 -*-
with open("frontend/js/dashboard.js", "r", encoding="utf-8") as f:
    dash_js = f.read()

target = """async function loadDashboardData(showNotification = false) {
    let summaryData = null;
    const filterEl = document.getElementById("dash-shift-filter");
    const selectedShift = filterEl ? filterEl.value : "1";
    const query = selectedShift ? `?shift_id=${encodeURIComponent(selectedShift)}` : "";"""

replacement = """async function loadDashboardData(showNotification = false) {
    let summaryData = null;
    const urlParams = new URLSearchParams(window.location.search);
    const preferredShiftId = urlParams.get("shift_id");
    const filterEl = document.getElementById("dash-shift-filter");
    const selectedShift = preferredShiftId || (filterEl ? filterEl.value : "1");
    const query = selectedShift ? `?shift_id=${encodeURIComponent(selectedShift)}` : "";"""

assert target in dash_js, "target not found in dashboard.js"
dash_js = dash_js.replace(target, replacement, 1)

with open("frontend/js/dashboard.js", "w", encoding="utf-8") as f:
    f.write(dash_js)

print("Updated frontend/js/dashboard.js successfully")
