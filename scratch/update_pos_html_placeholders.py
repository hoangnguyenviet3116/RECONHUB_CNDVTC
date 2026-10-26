# -*- coding: utf-8 -*-
with open('frontend/pos.html', 'r', encoding='utf-8') as f:
    c = f.read()

target1 = """                                <select id="pos-shift-select" class="form-select form-select-sm" required>
                                    <option value="1">Ca sáng — 24/10/2026</option>
                                </select>"""

replacement1 = """                                <select id="pos-shift-select" class="form-select form-select-sm" required>
                                    <option value="">Đang tải danh sách ca...</option>
                                </select>"""

assert target1 in c, "target1 not found in pos.html"
c = c.replace(target1, replacement1, 1)

target2 = """                                <select id="pos-filter-shift" class="form-select form-select-sm" style="width: auto;" title="Lọc theo ca làm việc">
                                    <option value="1">Ca sáng — 24/10/2026 (Ca 1)</option>
                                    <option value="ALL">Tất cả ca bán hàng</option>
                                </select>"""

replacement2 = """                                <select id="pos-filter-shift" class="form-select form-select-sm" style="width: auto;" title="Lọc theo ca làm việc">
                                    <option value="">Đang tải danh sách ca...</option>
                                </select>"""

assert target2 in c, "target2 not found in pos.html"
c = c.replace(target2, replacement2, 1)

with open('frontend/pos.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated frontend/pos.html successfully")
