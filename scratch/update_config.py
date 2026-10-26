with open("backend/config.py", "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

target = """    # Môi trường chạy hệ thống: 'production', 'development', 'test'
    # MẶC ĐỊNH AN TOÀN LÀ 'production': Không tự động nạp dữ liệu mẫu
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").strip().lower()

    # Chuỗi kết nối Database SQL Server"""

replacement = """    # Môi trường chạy hệ thống: 'production', 'development', 'test'
    # MẶC ĐỊNH AN TOÀN LÀ 'production': Không tự động nạp dữ liệu mẫu
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").strip().lower()

    # Cờ cho phép nạp dữ liệu mẫu: MẶC ĐỊNH LÀ FALSE (Chỉ bật khi cần kiểm thử dev/test)
    ENABLE_DB_SEED: bool = os.getenv("ENABLE_DB_SEED", "false").strip().lower() in ("true", "1", "yes")

    # Chuỗi kết nối Database SQL Server"""

target_methods = """    def is_test(self) -> bool:
        return self.ENVIRONMENT == "test"

    def get_database_url(self) -> str:"""

replacement_methods = """    def is_test(self) -> bool:
        return self.ENVIRONMENT in ("test", "testing")

    def is_seed_allowed(self) -> bool:
        \"\"\"
        Chỉ cho phép nạp dữ liệu mẫu khi:
        1. Môi trường KHÔNG PHẢI production
        2. Biến ENABLE_DB_SEED được bật tường minh (true)
        \"\"\"
        return (not self.is_production()) and self.ENABLE_DB_SEED

    def get_database_url(self) -> str:"""

assert target in content_norm, "Target not found in config.py"
assert target_methods in content_norm, "Target methods not found in config.py"

content_norm = content_norm.replace(target, replacement)
content_norm = content_norm.replace(target_methods, replacement_methods)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open("backend/config.py", "w", encoding="utf-8") as f:
    f.write(content_norm)

print("SUCCESS: backend/config.py updated")
