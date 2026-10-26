# -*- coding: utf-8 -*-
with open('frontend/js/shifts.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = """                                        : `
                                            <a href="dashboard.html?shift_id=${shift.id}" class="btn-fp-outline py-1 px-2" style="font-size:0.78rem;">
                                                Báo cáo ca
                                            </a>
                                            <button type="button" class="btn btn-sm btn-light border text-muted py-1 px-2" disabled style="font-size:0.75rem;">
                                                Đã đóng ca
                                            </button>
                                        `"""

replacement = """                                        : `
                                            <a href="pos.html?shift_id=${shift.id}" class="btn-fp-outline py-1 px-2" style="font-size:0.78rem;" title="Xem quầy thu ngân của ca này">
                                                Quầy thu ngân
                                            </a>
                                            <a href="dashboard.html?shift_id=${shift.id}" class="btn-fp-outline py-1 px-2" style="font-size:0.78rem;">
                                                Báo cáo ca
                                            </a>
                                            <button type="button" class="btn btn-sm btn-light border text-muted py-1 px-2" disabled style="font-size:0.75rem;">
                                                Đã đóng
                                            </button>
                                        `"""

assert target in c, "target not found in shifts.js"
c = c.replace(target, replacement, 1)

with open('frontend/js/shifts.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated frontend/js/shifts.js successfully")
