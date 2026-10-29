# -*- coding: utf-8 -*-
import sys

new_css = """

/* ==========================================================================
   PHONG CÁCH QUẢN LÝ CA BÁN HÀNG HIỆN ĐẠI (FINTECH SaaS STYLE)
   ========================================================================== */

/* 1. Header & Typography */
.shift-page-wrapper {
    max-width: 1160px;
    margin: 0 auto;
}

.shift-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    margin-bottom: 0.35rem;
}

.shift-main-title {
    font-size: 1.85rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin-bottom: 0.35rem;
}

.shift-sub-title {
    font-size: 0.94rem;
    color: #64748b;
    margin-bottom: 1.75rem;
}

/* 2. Khối mở ca làm việc mới */
.shift-create-card {
    background: #ffffff;
    border: 1px solid #eef2f6;
    border-radius: 18px;
    box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03);
    padding: 1.5rem 1.75rem;
}

.shift-create-card-header {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin-bottom: 1.35rem;
}

.shift-create-icon-badge {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: #eff6ff;
    color: #2563eb;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    font-weight: 600;
    flex-shrink: 0;
}

.shift-input-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #334155;
    margin-bottom: 0.4rem;
    display: block;
}

.shift-input {
    height: 44px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    font-size: 0.9rem;
    padding: 0.5rem 0.85rem;
    color: #0f172a;
    background-color: #ffffff;
    transition: all 0.18s ease;
}

.shift-input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    outline: none;
}

.shift-input-addon {
    height: 44px;
    border-top-right-radius: 10px !important;
    border-bottom-right-radius: 10px !important;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: none;
    color: #64748b;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0 0.85rem;
}

.btn-shift-create {
    height: 44px;
    background: #0f172a;
    color: #ffffff;
    border: 1px solid #0f172a;
    border-radius: 10px;
    padding: 0 1.5rem;
    font-size: 0.9rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    white-space: nowrap;
    transition: all 0.18s ease;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1);
}

.btn-shift-create:hover {
    background: #1e293b;
    color: #ffffff;
    border-color: #1e293b;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.15);
}

/* 3. Tiêu đề danh sách ca & Bộ lọc */
.shift-list-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-top: 2rem;
    margin-bottom: 1.25rem;
}

.shift-list-title {
    font-size: 1.18rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.2rem;
}

.shift-list-subtitle {
    font-size: 0.84rem;
    color: #64748b;
}

.shift-filter-select {
    height: 42px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    font-size: 0.85rem;
    font-weight: 500;
    color: #334155;
    background-color: #ffffff;
    padding: 0.45rem 2.2rem 0.45rem 0.95rem;
    cursor: pointer;
    min-width: 170px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.shift-filter-select:focus {
    border-color: #2563eb;
    outline: none;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.btn-shift-refresh {
    height: 42px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    color: #475569;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 0 0.9rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    transition: all 0.18s ease;
}

.btn-shift-refresh:hover {
    background-color: #f8fafc;
    color: #0f172a;
    border-color: #cbd5e1;
}

/* 4. Thẻ ca làm việc nằm ngang (Horizontal Shift Row Card) */
.shift-row-card {
    background: #ffffff;
    border: 1px solid #eef2f6;
    border-radius: 16px;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
    padding: 1.25rem 1.6rem;
    display: grid;
    grid-template-columns: 2.3fr 1.3fr 1fr 1.4fr auto;
    align-items: center;
    gap: 1.5rem;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.shift-row-card:hover {
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
    transform: translateY(-1px);
}

.shift-row-card.is-open {
    border-left: 4.5px solid #10b981;
}

.shift-row-card.is-closed {
    border-left: 4.5px solid #e2e8f0;
}

.shift-col-info {
    display: flex;
    align-items: center;
    gap: 0.95rem;
    min-width: 0;
}

.shift-icon-box {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.shift-icon-box.is-open {
    background: #ecfdf5;
    color: #10b981;
}

.shift-icon-box.is-closed {
    background: #f1f5f9;
    color: #64748b;
}

.shift-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.shift-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 9999px;
    font-size: 0.74rem;
    font-weight: 600;
    padding: 0.2rem 0.65rem;
    flex-shrink: 0;
}

.shift-status-pill.is-open {
    background: #dcfce7;
    color: #15803d;
}

.shift-status-pill.is-closed {
    background: #f1f5f9;
    color: #64748b;
}

.shift-code-time {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.shift-col-metric {
    min-width: 0;
}

.shift-metric-label {
    font-size: 0.75rem;
    color: #64748b;
    margin-bottom: 0.2rem;
    display: block;
    font-weight: 500;
}

.shift-metric-value {
    font-size: 1.02rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.25;
}

.shift-metric-sub {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.15rem;
    display: block;
}

.shift-col-progress {
    min-width: 120px;
}

.shift-progress-percent {
    font-size: 0.78rem;
    font-weight: 600;
    color: #0f172a;
}

.shift-progress-track {
    width: 100%;
    height: 6px;
    background: #f1f5f9;
    border-radius: 9999px;
    overflow: hidden;
}

.shift-progress-fill {
    height: 100%;
    background: #10b981;
    border-radius: 9999px;
    transition: width 0.3s ease;
}

.shift-col-actions {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-shrink: 0;
}

.btn-shift-action-pos {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    font-size: 0.84rem;
    font-weight: 600;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    white-space: nowrap;
    transition: all 0.18s ease;
}

.btn-shift-action-pos:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
    color: #0f172a;
    transform: translateY(-1px);
}

.btn-shift-action-close {
    background: #e11d48;
    color: #ffffff;
    border: 1px solid #e11d48;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    font-size: 0.84rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    white-space: nowrap;
    transition: all 0.18s ease;
    box-shadow: 0 2px 8px rgba(225, 29, 72, 0.18);
}

.btn-shift-action-close:hover {
    background: #be123c;
    border-color: #be123c;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(225, 29, 72, 0.25);
}

.btn-shift-action-detail {
    background: #ffffff;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.5rem 0.85rem;
    font-size: 0.82rem;
    font-weight: 500;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;
    transition: all 0.18s ease;
}

.btn-shift-action-detail:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
    color: #0f172a;
}

/* 5. Thanh Navbar Phong cách Hiện đại */
.fp-navbar-modern {
    background-color: #ffffff;
    border-bottom: 1px solid #eef2f6;
    padding: 0.75rem 0;
    position: sticky;
    top: 0;
    z-index: 1030;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.02);
}

.modern-brand-logo {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: #0f172a;
    color: #ffffff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.modern-nav-tab {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.9rem;
    border-radius: 8px;
    color: #475569;
    text-decoration: none;
    font-size: 0.88rem;
    font-weight: 500;
    transition: all 0.15s ease;
}

.modern-nav-tab:hover {
    color: #0f172a;
    background-color: #f8fafc;
}

.modern-nav-tab.active {
    color: #0f172a;
    font-weight: 600;
    background-color: #f1f5f9;
}

.modern-nav-tab.active .hi-icon {
    color: #2563eb;
}

.modern-role-box {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.modern-role-label {
    font-size: 0.82rem;
    color: #64748b;
    font-weight: 500;
}

.modern-role-select {
    height: 38px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    color: #0f172a;
    font-size: 0.84rem;
    font-weight: 600;
    padding: 0.35rem 2rem 0.35rem 0.85rem;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.modern-role-select:focus {
    border-color: #2563eb;
    outline: none;
}

/* Responsive cho Thẻ ca */
@media (max-width: 1199.98px) {
    .shift-row-card {
        grid-template-columns: 2fr 1.2fr 1fr 1.2fr auto;
        gap: 1rem;
        padding: 1.15rem 1.25rem;
    }
}

@media (max-width: 991.98px) {
    .shift-row-card {
        grid-template-columns: 1fr 1fr;
        gap: 1.25rem;
    }
    .shift-col-info {
        grid-column: 1 / -1;
    }
    .shift-col-actions {
        grid-column: 1 / -1;
        justify-content: flex-end;
    }
}

@media (max-width: 575.98px) {
    .shift-row-card {
        grid-template-columns: 1fr;
        gap: 1rem;
    }
    .shift-col-actions {
        justify-content: stretch;
        flex-direction: column;
    }
    .shift-col-actions a, .shift-col-actions button {
        width: 100%;
        justify-content: center;
    }
}
"""

with open("frontend/css/styles.css", "r", encoding="utf-8") as f:
    orig = f.read()

# Update --fp-bg-base
orig = orig.replace("--fp-bg-base: #f1f5f9;", "--fp-bg-base: #f8fafc;")

if "PHONG CÁCH QUẢN LÝ CA BÁN HÀNG HIỆN ĐẠI" not in orig:
    orig += new_css

with open("frontend/css/styles.css", "w", encoding="utf-8") as f:
    f.write(orig)

print("Updated frontend/css/styles.css successfully.")
