# -*- coding: utf-8 -*-

sim_css = """

/* ==========================================================================
   PHONG CÁCH CỔNG THANH TOÁN MÔ PHỎNG (FINTECH SIMULATOR STYLE)
   ========================================================================== */

/* 1. Khung thông tin tài khoản người nhận */
.sim-bank-account-box {
    background: #f8fafc;
    border: 1px solid #eef2f6;
    border-radius: 14px;
    padding: 0.95rem 1.15rem;
}

.sim-bank-avatar {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #1e3a8a;
    color: #ffffff;
    font-size: 0.9rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(30, 58, 138, 0.2);
}

.sim-bank-label {
    font-size: 0.72rem;
    color: #64748b;
    margin-bottom: 0.15rem;
}

.sim-bank-name {
    font-size: 0.92rem;
    font-weight: 700;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    line-height: 1.25;
}

.sim-bank-sub {
    font-size: 0.78rem;
    color: #64748b;
}

.sim-bank-check-icon {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #10b981;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

/* 2. Khung biên lai kết quả */
.sim-receipt-card {
    background: #ffffff;
    border: 1px solid #eef2f6;
    border-radius: 18px;
    box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03);
    padding: 1.5rem;
    min-height: 440px;
    display: flex;
    flex-direction: column;
}

.sim-empty-receipt {
    margin: auto;
    text-align: center;
    padding: 2.5rem 1.5rem;
}

.sim-empty-icon {
    width: 58px;
    height: 58px;
    border-radius: 16px;
    background: #f1f5f9;
    color: #94a3b8;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.15rem;
}

/* 3. Bảng lịch sử giao dịch */
.sim-amount-pos {
    color: #10b981;
    font-weight: 700;
}
"""

with open("frontend/css/styles.css", "r", encoding="utf-8") as f:
    orig = f.read()

if "PHONG CÁCH CỔNG THANH TOÁN MÔ PHỎNG" not in orig:
    orig += sim_css

with open("frontend/css/styles.css", "w", encoding="utf-8") as f:
    f.write(orig)

print("Updated styles.css with simulator styles successfully.")
