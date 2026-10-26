with open("backend/seed.py", "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

target = """    # 1. BẢO VỆ MÔI TRƯỜNG PRODUCTION: CHẶN HOÀN TOÀN
    if settings.is_production():
        print("\\n[LỖI BẢO VỆ - THAO TÁC BỊ TỪ CHỐI]")
        print("Môi trường hiện tại là PRODUCTION!")
        print("Hệ thống nghiêm cấm nạp dữ liệu mẫu (seed_data.sql) vào môi trường vận hành thật.")
        print("Môi trường thật chỉ được tiếp nhận dữ liệu từ các hoạt động thực tế trên giao diện web.")
        print("Để chạy dữ liệu mẫu phục vụ kiểm thử, vui lòng đổi biến môi trường sang 'development' hoặc 'test':")
        print("  Windows PowerShell: $env:ENVIRONMENT='development'; python backend/seed.py --confirm")
        print("  File .env:         ENVIRONMENT=development")
        sys.exit(1)"""

replacement = """    # 1. BẢO VỆ MÔI TRƯỜNG PRODUCTION: CHẶN HOÀN TOÀN
    if settings.is_production():
        print("\\n[LỖI BẢO VỆ - THAO TÁC BỊ TỪ CHỐI]")
        print("Môi trường hiện tại là PRODUCTION!")
        print("Hệ thống nghiêm cấm nạp dữ liệu mẫu (seed_data.sql) vào môi trường vận hành thật.")
        print("Môi trường thật chỉ được tiếp nhận dữ liệu từ các hoạt động thực tế trên giao diện web.")
        print("Để chạy dữ liệu mẫu phục vụ kiểm thử, vui lòng đổi biến môi trường sang 'development' hoặc 'test':")
        print("  Windows PowerShell: $env:ENVIRONMENT='development'; $env:ENABLE_DB_SEED='true'; python backend/seed.py --confirm")
        print("  File .env:         ENVIRONMENT=development")
        print("                     ENABLE_DB_SEED=true")
        sys.exit(1)

    # 2. KIỂM TRA CỜ ENABLE_DB_SEED TRONG DEV / TEST
    if not settings.ENABLE_DB_SEED:
        print("\\n[THAO TÁC BỊ CHẶN BỞI CỜ BẢO VỆ]")
        print("Biến ENABLE_DB_SEED hiện đang tắt (false).")
        print("Để nạp dữ liệu mẫu trong môi trường thử nghiệm, bạn phải bật cờ ENABLE_DB_SEED=true:")
        print("  Windows PowerShell: $env:ENABLE_DB_SEED='true'; python backend/seed.py --confirm")
        print("  File .env:         ENABLE_DB_SEED=true")
        sys.exit(1)"""

assert target in content_norm, "Target not found in seed.py"
content_norm = content_norm.replace(target, replacement)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open("backend/seed.py", "w", encoding="utf-8") as f:
    f.write(content_norm)

print("SUCCESS: backend/seed.py updated")
