with open("backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

target_import = "from routers import shifts, orders, payment_requests, webhooks, mock_bank, decisions, dashboard"
replacement_import = "from routers import shifts, orders, payment_requests, webhooks, mock_bank, decisions, dashboard, events"

target_router = "app.include_router(dashboard.router)"
replacement_router = "app.include_router(dashboard.router)\napp.include_router(events.router)"

assert target_import in content_norm, "target_import not found in main.py"
assert target_router in content_norm, "target_router not found in main.py"

content_norm = content_norm.replace(target_import, replacement_import)
content_norm = content_norm.replace(target_router, replacement_router)

if "\r\n" in content:
    content_norm = content_norm.replace("\n", "\r\n")

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(content_norm)

print("SUCCESS: backend/main.py updated with events router")
