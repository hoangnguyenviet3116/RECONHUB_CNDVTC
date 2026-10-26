path = r"C:\Users\DELL\.gemini\antigravity\brain\eaa355ea-b9b1-4ad7-8777-6c7bd0c13e51\scratch\run_qa_test_suite.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

target = """def reset_database():
    with open('database/seed_data.sql', 'r', encoding='utf-8') as f:
        sql = f.read()"""

replacement = """def reset_database():
    from config import settings
    if settings.is_production() and not settings.ENABLE_DB_SEED:
        print("\\n[BẢO VỆ PRODUCTION] Hệ thống đang ở chế độ PRODUCTION và ENABLE_DB_SEED=false.")
        print("Hệ thống nghiêm cấm tự động nạp seed_data.sql vào cơ sở dữ liệu production.")
        print("Để chạy bộ test QA đặc tả TC-01 đến TC-10, vui lòng thiết lập biến môi trường:")
        print("  Windows PowerShell: $env:ENVIRONMENT='test'; $env:ENABLE_DB_SEED='true'")
        print("  Hoặc trong file .env: ENVIRONMENT=test, ENABLE_DB_SEED=true")
        sys.exit(1)
    with open('database/seed_data.sql', 'r', encoding='utf-8') as f:
        sql = f.read()"""

assert target in content_norm, "Target not found in run_qa_test_suite.py"
content_norm = content_norm.replace(target, replacement)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open(path, "w", encoding="utf-8") as f:
    f.write(content_norm)

print("SUCCESS: run_qa_test_suite.py updated with production guard")
