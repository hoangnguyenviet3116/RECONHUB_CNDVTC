# -*- coding: utf-8 -*-
"""
Verification Script: Test 100% Data Synchronization between POS orders and Dashboard Summary
"""
import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "X-Demo-Role": "OWNER",
            "X-Merchant-Id": "1",
            "X-User-Id": "1"
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def verify_sync():
    print("=" * 80)
    print("KIEM TRA DOI SOAT DONG BO DU LIEU: QUAY THU NGAN (POS) vs DASHBOARD SO QUY")
    print("=" * 80)

    # 1. Fetch all orders (as POS does)
    orders = get_json(f"{BASE_URL}/orders")
    print(f"\n[1] Lay danh sach hoa don tu /orders: Tong so {len(orders)} don hang")

    # 2. Fetch available shifts
    shifts_res = get_json(f"{BASE_URL}/shifts")
    shift_ids = [str(s["id"]) for s in shifts_res] + ["3", "ALL"]
    print(f"[2] Cac pham vi ca kiem tra: {shift_ids}")

    for shift_filter in shift_ids:
        print(f"\n" + "-" * 60)
        print(f">>> KIEM TRA PHAM VI CA: {shift_filter}")
        print("-" * 60)

        # A. POS calculation logic (replicated exactly from pos.js)
        pos_scoped_orders = [
            o for o in orders
            if shift_filter == "ALL" or str(o.get("shift_id")) == shift_filter
        ]
        
        pos_total_all = sum(float(o["total_amount"]) for o in pos_scoped_orders)
        pos_valid_orders = [
            o for o in pos_scoped_orders
            if o.get("order_status") in ["CONFIRMED_ORDER", "UNDER_REVIEW"]
        ]
        pos_cancelled_orders = [
            o for o in pos_scoped_orders
            if o.get("order_status") == "CANCELLED_ORDER"
        ]

        pos_valid_total = sum(float(o["total_amount"]) for o in pos_valid_orders)
        pos_cancelled_total = sum(float(o["total_amount"]) for o in pos_cancelled_orders)
        pos_paid_total = sum(
            float(o.get("net_paid_amount") or o.get("allocated_amount") or (float(o["total_amount"]) if o.get("payment_status") == "PAID" else 0))
            for o in pos_valid_orders
        )
        pos_remaining_total = max(0.0, pos_valid_total - pos_paid_total)

        print(f"  [POS Quay Thu Ngan] So hoa don: {len(pos_scoped_orders)} (Hop le: {len(pos_valid_orders)}, Da huy: {len(pos_cancelled_orders)})")
        print(f"    - Tong hien thi:     {pos_total_all:,.0f} VND")
        print(f"    - Hop le (So quy):   {pos_valid_total:,.0f} VND")
        print(f"    - Da huy (Loai tru): {pos_cancelled_total:,.0f} VND")
        print(f"    - Thuc thu:          {pos_paid_total:,.0f} VND")
        print(f"    - Con thieu:         {pos_remaining_total:,.0f} VND")

        # B. Dashboard summary from API
        dash_summary = get_json(f"{BASE_URL}/dashboard/summary?shift_id={shift_filter}")
        dash_valid_total = float(dash_summary["valid_order_total"])
        dash_cancelled_total = float(dash_summary.get("cancelled_order_total", 0.0))
        dash_paid_total = float(dash_summary["allocated_payment_total"])
        dash_remaining_total = float(dash_summary["remaining_receivable"])

        print(f"\n  [Dashboard So Quy] Ca: {dash_summary['shift_name']} (Muc tieu: {dash_summary['target_revenue']:,.0f} VND)")
        print(f"    - Tong hoa don hop le: {dash_valid_total:,.0f} VND")
        print(f"    - Don huy (Loai tru):  {dash_cancelled_total:,.0f} VND")
        print(f"    - Thuc thu da khop:    {dash_paid_total:,.0f} VND")
        print(f"    - Con phai thu:        {dash_remaining_total:,.0f} VND")

        # C. Compare
        assert pos_valid_total == dash_valid_total, f"LECH TONG HOA DON HOP LE! POS={pos_valid_total} vs DASH={dash_valid_total}"
        assert pos_cancelled_total == dash_cancelled_total, f"LECH TIEN HOA DON HUY! POS={pos_cancelled_total} vs DASH={dash_cancelled_total}"
        assert pos_paid_total == dash_paid_total, f"LECH TIEN THUC THU! POS={pos_paid_total} vs DASH={dash_paid_total}"
        assert pos_remaining_total == dash_remaining_total, f"LECH TIEN CON PHAI THU! POS={pos_remaining_total} vs DASH={dash_remaining_total}"

        print(f"\n  ===> KET QUA DOI SOAT: [KHOP 100% TUYET DOI] (POS == DASHBOARD)")

    print("\n" + "=" * 80)
    print("HOAN TAT KIEM THU: DU LIEU DA DONG BO 100% GIUA QUAY THU NGAN VA SO QUY DASHBOARD!")
    print("=" * 80)

if __name__ == "__main__":
    verify_sync()
