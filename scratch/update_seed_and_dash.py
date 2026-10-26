with open("database/seed_data.sql", "r", encoding="utf-8") as f:
    sql = f.read()

header = """-- =============================================================================
-- [CẢNH BÁO AN TOÀN - DEVELOPMENT / TEST ONLY]
-- FILE NÀY CHỈ DÙNG CHO MÔI TRƯỜNG THỬ NGHIỆM VÀ PHÁT TRIỂN (DEV / TEST).
-- NGHIÊM CẤM TỰ ĐỘNG CHẠY HOẶC NẠP FILE NÀY TRONG MÔI TRƯỜNG PRODUCTION.
-- HỆ THỐNG VẬN HÀNH THẬT CHỈ LẤY VÀ HIỂN THỊ DỮ LIỆU PHÁT SINH TỪ WEB.
-- =============================================================================

"""

if "-- [CẢNH BÁO AN TOÀN" not in sql:
    sql = header + sql
    with open("database/seed_data.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    print("SUCCESS: database/seed_data.sql updated with warning header")


# Update frontend/js/dashboard.js
with open("frontend/js/dashboard.js", "r", encoding="utf-8") as f:
    dash_js = f.read()

dash_norm = dash_js.replace("\r\n", "\n")

target_tbody = """    if (!tbody) return;
    tbody.innerHTML = entries"""

replacement_tbody = """    if (!tbody) return;
    if (entries.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-secondary">
                    Chưa có bút toán nào trong sổ cái. Bút toán sẽ tự động hình thành khi có thanh toán thực tế trên web.
                </td>
            </tr>
        `;
        return;
    }
    tbody.innerHTML = entries"""

assert target_tbody in dash_norm, "Target tbody not found"
dash_norm = dash_norm.replace(target_tbody, replacement_tbody)

if "\r\n" in dash_js:
    dash_norm = dash_norm.replace("\n", "\r\n")

with open("frontend/js/dashboard.js", "w", encoding="utf-8") as f:
    f.write(dash_norm)
print("SUCCESS: frontend/js/dashboard.js updated")
