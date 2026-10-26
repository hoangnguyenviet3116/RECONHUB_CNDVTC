# -*- coding: utf-8 -*-
"""
Script applying complete frontend & backend synchronization fixes for VietQR ReconHub
"""
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

# =========================================================================
# 1. UPDATE frontend/dashboard.html
# =========================================================================
with open("frontend/dashboard.html", "r", encoding="utf-8") as f:
    dash_html = f.read()

# Add valid order count and cancelled order row under kpi-valid-order-total
target_kpi_card = """<div class="h3 fw-bold text-primary mb-1 font-numeric" id="kpi-valid-order-total">100.000.000 ₫</div>
                            <div class="d-flex justify-content-between small text-secondary pt-2 border-top" style="font-size: 0.76rem;">
                                <span>Mục tiêu ca:</span>
                                <strong class="text-dark font-numeric" id="kpi-target-revenue">120.000.000 ₫</strong>
                            </div>"""

replacement_kpi_card = """<div class="h3 fw-bold text-primary mb-1 font-numeric" id="kpi-valid-order-total">100.000.000 ₫</div>
                            <div class="d-flex justify-content-between small text-secondary pt-2 border-top" style="font-size: 0.76rem;">
                                <span>Mục tiêu ca:</span>
                                <strong class="text-dark font-numeric" id="kpi-target-revenue">120.000.000 ₫</strong>
                            </div>
                            <div class="d-flex justify-content-between small text-secondary pt-1" style="font-size: 0.76rem;">
                                <span>Đơn hợp lệ:</span>
                                <strong class="text-dark font-numeric" id="dash-valid-order-count">0 đơn</strong>
                            </div>
                            <div class="d-flex justify-content-between small text-danger pt-1" style="font-size: 0.76rem;" id="dash-cancelled-order-row">
                                <span>Đơn đã hủy:</span>
                                <span class="font-numeric" id="dash-cancelled-order-total">0 ₫ (0 đơn)</span>
                            </div>"""

dash_html = dash_html.replace(target_kpi_card, replacement_kpi_card)

# Add Tab 3 button
target_tab_nav = """                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="tab-finance-table" data-bs-toggle="tab" data-bs-target="#pane-finance-table" type="button" role="tab">
                                Bảng Cân Đối Dòng Tiền Chi Tiết
                            </button>
                        </li>"""

replacement_tab_nav = """                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="tab-finance-table" data-bs-toggle="tab" data-bs-target="#pane-finance-table" type="button" role="tab">
                                Bảng Cân Đối Dòng Tiền Chi Tiết
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="tab-orders-detail" data-bs-toggle="tab" data-bs-target="#pane-orders-detail" type="button" role="tab">
                                Danh Sách Hóa Đơn Đối Soát
                            </button>
                        </li>"""

dash_html = dash_html.replace(target_tab_nav, replacement_tab_nav)

# Add Tab 3 pane
target_tab_pane_end = """                    <!-- Tab 2: Bảng cân đối dòng tiền chi tiết -->
                    <div class="tab-pane fade" id="pane-finance-table" role="tabpanel">
                        <div class="table-responsive">
                            <table class="fp-table">
                                <thead>
                                    <tr>
                                        <th>Hạng mục đối soát</th>
                                        <th>Ý nghĩa quản lý</th>
                                        <th class="text-end">Số tiền (VNĐ)</th>
                                    </tr>
                                </thead>
                                <tbody id="dash-reconciliation-formula-tbody"></tbody>
                            </table>
                        </div>
                    </div>
                </div>"""

replacement_tab_pane_end = """                    <!-- Tab 2: Bảng cân đối dòng tiền chi tiết -->
                    <div class="tab-pane fade" id="pane-finance-table" role="tabpanel">
                        <div class="table-responsive">
                            <table class="fp-table">
                                <thead>
                                    <tr>
                                        <th>Hạng mục đối soát</th>
                                        <th>Ý nghĩa quản lý</th>
                                        <th class="text-end">Số tiền (VNĐ)</th>
                                    </tr>
                                </thead>
                                <tbody id="dash-reconciliation-formula-tbody"></tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Tab 3: Danh sách hóa đơn đối soát -->
                    <div class="tab-pane fade" id="pane-orders-detail" role="tabpanel">
                        <div class="alert alert-info py-2 px-3 rounded-3 border-0 small mb-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
                            <div>
                                <strong>Nguyên tắc kế toán:</strong> Chỉ các đơn hàng <code>CONFIRMED_ORDER</code> và <code>UNDER_REVIEW</code> mới được tính vào <strong>Tổng hóa đơn hợp lệ (Sổ quỹ)</strong>. Hóa đơn hủy <code>CANCELLED_ORDER</code> bị loại trừ khỏi doanh thu phải thu.
                            </div>
                            <span class="badge bg-primary" id="dash-orders-count-badge">0 đơn</span>
                        </div>
                        <div class="table-responsive">
                            <table class="fp-table">
                                <thead>
                                    <tr>
                                        <th>Mã hóa đơn</th>
                                        <th>Ca bán hàng</th>
                                        <th class="text-end">Tổng tiền</th>
                                        <th class="text-end">Đã thu</th>
                                        <th class="text-end">Còn thiếu</th>
                                        <th>Trạng thái đơn</th>
                                        <th>Trạng thái thanh toán</th>
                                        <th>Hạch toán sổ quỹ</th>
                                    </tr>
                                </thead>
                                <tbody id="dash-orders-table-tbody">
                                    <tr>
                                        <td colspan="8" class="text-center py-4 text-secondary">
                                            Đang tải danh sách hóa đơn đối soát...
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""

dash_html = dash_html.replace(target_tab_pane_end, replacement_tab_pane_end)

with open("frontend/dashboard.html", "w", encoding="utf-8") as f:
    f.write(dash_html)
print("Updated frontend/dashboard.html successfully.")

# =========================================================================
# 2. UPDATE frontend/pos.html
# =========================================================================
with open("frontend/pos.html", "r", encoding="utf-8") as f:
    pos_html = f.read()

# Add pos-filter-shift to filter header
target_pos_filter = """                            <div class="d-flex flex-wrap align-items-center gap-2">
                                <select id="pos-filter-payment" class="form-select form-select-sm" style="width: auto;">"""

replacement_pos_filter = """                            <div class="d-flex flex-wrap align-items-center gap-2">
                                <select id="pos-filter-shift" class="form-select form-select-sm" style="width: auto;" title="Lọc theo ca làm việc">
                                    <option value="1">Ca sáng — 24/10/2026 (Ca 1)</option>
                                    <option value="ALL">Tất cả ca bán hàng</option>
                                </select>

                                <select id="pos-filter-payment" class="form-select form-select-sm" style="width: auto;">"""

pos_html = pos_html.replace(target_pos_filter, replacement_pos_filter)

# Add pos summary bar right above table-responsive
target_pos_table_start = """                        <div class="table-responsive">
                            <table class="fp-table">"""

replacement_pos_table_start = """                        <!-- Thanh tổng hợp đối soát nhanh hóa đơn tại quầy -->
                        <div class="pos-summary-bar d-flex flex-wrap align-items-center justify-content-between gap-2 p-2 px-3 rounded-3 bg-light border mb-3 small">
                            <div>
                                <span class="text-secondary">Tổng hiển thị:</span>
                                <strong class="font-numeric text-dark" id="pos-stat-total">0 ₫</strong>
                                <span class="text-muted" style="font-size:0.75rem;" id="pos-stat-count">(0 đơn)</span>
                            </div>
                            <div>
                                <span class="text-secondary">Hợp lệ (Sổ quỹ):</span>
                                <strong class="font-numeric text-primary" id="pos-stat-valid">0 ₫</strong>
                            </div>
                            <div>
                                <span class="text-secondary">Đã thu:</span>
                                <strong class="font-numeric text-success" id="pos-stat-paid">0 ₫</strong>
                            </div>
                            <div>
                                <span class="text-secondary">Còn thiếu:</span>
                                <strong class="font-numeric text-warning" id="pos-stat-remaining">0 ₫</strong>
                            </div>
                        </div>

                        <div class="table-responsive">
                            <table class="fp-table">"""

pos_html = pos_html.replace(target_pos_table_start, replacement_pos_table_start)

with open("frontend/pos.html", "w", encoding="utf-8") as f:
    f.write(pos_html)
print("Updated frontend/pos.html successfully.")
