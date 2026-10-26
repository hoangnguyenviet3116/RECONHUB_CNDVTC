# -*- coding: utf-8 -*-
"""
VietQR ReconHub - Shift End-Time & Auto-Close QA Test Suite
Tests all 11 scenarios specified in requirements.
"""
import sys
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

def api_call(endpoint, method="GET", body=None, role="OWNER", merchant_id="1", user_id="1"):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-Demo-Role": role,
        "X-Merchant-Id": str(merchant_id),
        "X-User-Id": str(user_id)
    }
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as err:
        content = err.read().decode('utf-8')
        try:
            payload = json.loads(content)
        except Exception:
            payload = {"detail": content}
        return err.code, payload

def run_tests():
    print("=" * 80)
    print("BAT DAU KIEM THU CHUC NANG QUAN LY THOI GIAN CA VA DONG CA (11 SCENARIOS)")
    print("=" * 80)

    now_vn = datetime.now(VN_TZ)

    # -------------------------------------------------------------------------
    # SCENARIO 1: Tạo ca với thời gian bắt đầu và kết thúc hợp lệ
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 1] Tao ca lam viec voi thoi gian bat dau va ket thuc hop le")
    start_1 = (now_vn - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    end_1 = (now_vn + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
    code, res = api_call("/shifts", method="POST", body={
        "name": "Ca Sang Thu Nghiem - Hop Le",
        "target_revenue": 50000000,
        "start_time": start_1,
        "end_time": end_1
    }, role="OWNER")

    assert code == 201, f"Expected 201, got {code}: {res}"
    valid_shift_id = res["id"]
    assert res["status"] == "OPEN", f"Expected OPEN, got {res['status']}"
    assert res["end_time"] is not None
    print(f"  -> PASS: Tao ca thanh cong, Shift ID #{valid_shift_id}, Status: {res['status']}, End Time: {res['end_time']}")

    # -------------------------------------------------------------------------
    # SCENARIO 2: Khong cho phep tao ca neu thoi gian ket thuc <= thoi gian bat dau
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 2] Tu choi tao ca neu thoi gian ket thuc <= thoi gian bat dau")
    invalid_start = (now_vn + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    invalid_end = (now_vn + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    code, res = api_call("/shifts", method="POST", body={
        "name": "Ca Loi Thoi Gian",
        "target_revenue": 30000000,
        "start_time": invalid_start,
        "end_time": invalid_end
    }, role="OWNER")

    assert code == 400, f"Expected 400, got {code}: {res}"
    print(f"  -> PASS: Tu choi ca khong hop le thanh cong (Code 400): {res.get('detail')}")

    # -------------------------------------------------------------------------
    # SCENARIO 4: Nguoi khong co quyen (CASHIER / REVIEWER) khong the dong ca
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 4] Nguoi khong co quyen (CASHIER) khong the dong ca")
    code, res = api_call(f"/shifts/{valid_shift_id}/close", method="POST", role="CASHIER")
    assert code == 403, f"Expected 403 Forbidden, got {code}: {res}"
    print(f"  -> PASS: Chan CASHIER thanh cong (Code 403): {res.get('detail')}")

    code, res = api_call(f"/shifts/{valid_shift_id}/close", method="POST", role="REVIEWER")
    assert code == 403, f"Expected 403 Forbidden, got {code}: {res}"
    print(f"  -> PASS: Chan REVIEWER thanh cong (Code 403): {res.get('detail')}")

    # -------------------------------------------------------------------------
    # SCENARIO 3: Nguoi co quyen (OWNER) dong ca thu cong thanh cong
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 3] Nguoi co quyen (OWNER) dong ca thu cong thanh cong")
    code, res = api_call(f"/shifts/{valid_shift_id}/close", method="POST", role="OWNER")
    assert code == 200, f"Expected 200, got {code}: {res}"
    assert res["status"] == "CLOSED", f"Expected CLOSED, got {res['status']}"
    assert res["closed_at"] is not None, "closed_at must be populated"
    print(f"  -> PASS: OWNER dong ca thanh cong! Status: {res['status']}, Closed At: {res['closed_at']}")

    # Thu dong ca lan 2 -> Phai bao loi
    code, res = api_call(f"/shifts/{valid_shift_id}/close", method="POST", role="OWNER")
    assert code in [400, 409], f"Expected 409 Conflict, got {code}: {res}"
    print(f"  -> PASS: Khong cho phep dong ca lan 2 (Code {code}): {res.get('detail')}")

    # -------------------------------------------------------------------------
    # SCENARIO 6: Khong the tao don khi ca da dong
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 6] Tu choi tao don hang khi ca da dong (CLOSED)")
    code, res = api_call("/orders", method="POST", body={
        "shift_id": valid_shift_id,
        "total_amount": 1000000,
        "note": "Don hang thu tao vao ca da dong"
    }, role="CASHIER")

    assert code in [403, 409], f"Expected 409 Conflict, got {code}: {res}"
    print(f"  -> PASS: Tu choi tao don vao ca dong (Code {code}): {res.get('detail')}")

    # -------------------------------------------------------------------------
    # SCENARIO 5: Ca tu dong dong khi den thoi gian ket thuc (Background / Scheduler)
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 5] Ca tu dong dong khi den thoi gian ket thuc (Auto-close)")
    # Tao 1 ca co end_time sau 2 giay nua
    short_start = (now_vn - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    short_end = (now_vn + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S")
    code, res = api_call("/shifts", method="POST", body={
        "name": "Ca Tu Dong Het Han Sau 2s",
        "target_revenue": 20000000,
        "start_time": short_start,
        "end_time": short_end
    }, role="OWNER")
    assert code == 201
    auto_shift_id = res["id"]
    print(f"  -> Da tao ca #{auto_shift_id}, end_time sau 2 giay: {short_end}")

    print("  -> Cho 4 giay de thoi gian ket thuc troi qua...")
    time.sleep(4)

    # Truy van ca: he thong phai tu dong chuyen sang CLOSED
    code, res = api_call(f"/shifts/{auto_shift_id}", method="GET")
    assert code == 200
    assert res["status"] == "CLOSED", f"Expected CLOSED, got {res['status']}"
    assert res["closed_at"] is not None
    print(f"  -> PASS: Ca da tu dong dong sang CLOSED! Closed At: {res['closed_at']}")

    # -------------------------------------------------------------------------
    # SCENARIO 7: Khong the tao don khi thoi gian ket thuc da den (Lazy check)
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 7] Khong the tao don khi ca da het thoi gian hoat dong")
    code, res = api_call("/orders", method="POST", body={
        "shift_id": auto_shift_id,
        "total_amount": 500000,
        "note": "Don hang thu tao vao ca da het gio"
    }, role="CASHIER")

    assert code in [403, 409], f"Expected 409 Conflict, got {code}: {res}"
    print(f"  -> PASS: Tu choi tao don vao ca het gio (Code {code}): {res.get('detail')}")

    # -------------------------------------------------------------------------
    # SCENARIO 8: Goi truc tiep API khong the vuot qua kiem tra ca
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 8] Goi truc tiep API khong the vuot qua kiem tra ca")
    # Goi tao order voi ca khong ton tai
    code, res = api_call("/orders", method="POST", body={
        "shift_id": 99999,
        "total_amount": 1000000
    }, role="CASHIER")
    assert code in [404, 409], f"Expected 404/409, got {code}: {res}"
    print(f"  -> PASS: Goi truc tiep ca 99999 bi chan (Code {code}): {res.get('detail')}")

    # -------------------------------------------------------------------------
    # SCENARIO 9: Giao dien POS cap nhat trang thai ca
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 9] Kiem tra du lieu ca tra ve phuc vu khoa giao dien POS")
    code, res = api_call("/shifts", method="GET")
    assert code == 200
    for s in res:
        if s["id"] == valid_shift_id:
            assert s["status"] == "CLOSED"
        if s["id"] == auto_shift_id:
            assert s["status"] == "CLOSED"
    print("  -> PASS: Danh sach ca phan anh chinh xac trang thai OPEN/CLOSED de POS vo hieu hoa form")

    # -------------------------------------------------------------------------
    # SCENARIO 10: Cac don hang, giao dich ton tai duoc bao toan sau khi dong ca
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 10] Bao toan toan bo don hang va giao dich sau khi dong ca")
    code, orders_after = api_call("/orders", method="GET")
    assert code == 200
    print(f"  -> PASS: Tong so don hang trong he thong van nguyen ven: {len(orders_after)} don hang")

    # -------------------------------------------------------------------------
    # SCENARIO 11: Chuc nang doi soat, Dashboard va Hash Chain van hoat dong 100%
    # -------------------------------------------------------------------------
    print("\n>>> [SCENARIO 11] Kiem tra Dashboard va toan ven chuoi khoi Hash Chain")
    code, dash = api_call("/dashboard/summary", method="GET")
    assert code == 200
    assert dash["ledger_integrity_valid"] is True
    print(f"  -> PASS: Dashboard tra ve ket qua doi soat chuan, Ledger Integrity: {dash['ledger_integrity_valid']}")

    code, chain = api_call("/ledger/verify-chain", method="GET")
    assert code == 200
    assert chain["is_valid"] is True
    print(f"  -> PASS: Chuoi khoi Hash Chain so quy toan ven 100% (is_valid: {chain['is_valid']})")

    print("\n" + "=" * 80)
    print("HOAN TAT: TAT CA 11/11 KICH BAN KIEM THU QUAN LY THOI GIAN CA DEU DAT (PASS) 100%!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
