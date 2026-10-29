# -*- coding: utf-8 -*-

pos_css = """

/* ==========================================================================
   PHONG CÁCH QUẦY THU NGÂN HIỆN ĐẠI (FINTECH POS STYLE)
   ========================================================================== */

/* 1. Ô nhập số tiền lớn & Nút nhập nhanh */
.pos-amount-input {
    height: 48px !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    border-radius: 10px 0 0 10px !important;
    border: 1px solid #e2e8f0 !important;
    padding: 0.4rem 0.85rem !important;
}

.pos-amount-input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    outline: none;
}

.pos-quick-btn {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.25rem 0.65rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s ease;
}

.pos-quick-btn:hover {
    background-color: #eff6ff;
    color: #2563eb;
    border-color: #bfdbfe;
    transform: translateY(-1px);
}

.btn-pos-create {
    height: 46px;
    background: #0f172a;
    color: #ffffff;
    border: 1px solid #0f172a;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.92rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    transition: all 0.18s ease;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1);
}

.btn-pos-create:hover {
    background: #1e293b;
    color: #ffffff;
    border-color: #1e293b;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.15);
}

.btn-pos-create:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: none !important;
}

/* 2. Thẻ Loa báo nhận tiền */
.pos-toggle-switch {
    width: 44px !important;
    height: 24px !important;
    cursor: pointer;
    background-color: #cbd5e1;
    border: none;
    transition: background-color 0.2s ease;
}

.pos-toggle-switch:checked {
    background-color: #10b981 !important;
}

.pos-tts-box {
    background: #f8fafc;
    border: 1px solid #eef2f6;
    border-radius: 14px;
    padding: 1rem 1.15rem;
}

.pos-tts-quote {
    font-size: 0.85rem;
    font-weight: 500;
    color: #1e293b;
    line-height: 1.5;
    font-style: italic;
}

.pos-tts-time {
    font-size: 0.74rem;
    color: #64748b;
}

/* 3. Bộ lọc & Tìm kiếm tại bảng Hóa đơn */
.pos-filter-select {
    height: 38px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    font-size: 0.84rem;
    background-color: #ffffff;
    color: #334155;
    padding: 0.35rem 1.8rem 0.35rem 0.75rem;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.pos-filter-select:focus {
    border-color: #2563eb;
    outline: none;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.pos-search-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
}

.pos-search-icon {
    position: absolute;
    left: 10px;
    color: #94a3b8;
    pointer-events: none;
    width: 15px;
    height: 15px;
}

.pos-search-input {
    height: 38px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    font-size: 0.84rem;
    padding-left: 32px;
    width: 175px;
    background-color: #ffffff;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.pos-search-input:focus {
    border-color: #2563eb;
    outline: none;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

/* 4. Thanh tổng hợp đối soát 4 chỉ số (KPI Bar) */
.pos-kpi-summary-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: #f8fafc;
    border: 1px solid #eef2f6;
    border-radius: 14px;
    padding: 0.9rem 1.25rem;
    gap: 1rem;
}

.pos-kpi-item {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

.pos-kpi-label {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 500;
}

.pos-kpi-val {
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.2;
}

.pos-kpi-count {
    font-size: 0.75rem;
    font-weight: 400;
    color: #64748b;
}

/* 5. Bảng hóa đơn chuẩn Retail Finance */
.pos-modern-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
}

.pos-modern-table thead th {
    background-color: #ffffff;
    color: #64748b;
    font-weight: 700;
    font-size: 0.74rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 0.75rem 0.85rem;
    border-bottom: 1.5px solid #eef2f6;
}

.pos-modern-table tbody td {
    padding: 0.95rem 0.85rem;
    vertical-align: middle;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.88rem;
    background-color: #ffffff;
}

.pos-modern-table tbody tr:hover td {
    background-color: #f8fafc;
}

/* 6. Nút Thao tác & Nhãn Trạng thái */
.btn-pos-receipt {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.35rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;
    transition: all 0.15s ease;
    cursor: pointer;
}

.btn-pos-receipt:hover {
    background: #f8fafc;
    color: #0f172a;
    border-color: #cbd5e1;
    transform: translateY(-1px);
}

.btn-pos-qr {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.35rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;
    transition: all 0.15s ease;
    cursor: pointer;
}

.btn-pos-qr:hover {
    background: #f8fafc;
    color: #0f172a;
    border-color: #cbd5e1;
    transform: translateY(-1px);
}

.pos-status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.22rem 0.75rem;
    white-space: nowrap;
}

.pos-status-paid {
    background-color: #dcfce7;
    color: #15803d;
}

.pos-status-partial {
    background-color: #fef3c7;
    color: #b45309;
}

.pos-status-unpaid {
    background-color: #eff6ff;
    color: #1d4ed8;
}

.pos-status-cancelled {
    background-color: #ffe4e6;
    color: #e11d48;
}

@media (max-width: 991.98px) {
    .pos-kpi-summary-row {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 575.98px) {
    .pos-kpi-summary-row {
        grid-template-columns: 1fr;
    }
}
"""

with open("frontend/css/styles.css", "r", encoding="utf-8") as f:
    orig = f.read()

if "PHONG CÁCH QUẦY THU NGÂN HIỆN ĐẠI" not in orig:
    orig += pos_css

with open("frontend/css/styles.css", "w", encoding="utf-8") as f:
    f.write(orig)

print("Updated styles.css with POS styles successfully.")
