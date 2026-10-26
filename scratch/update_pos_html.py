with open("frontend/pos.html", "r", encoding="utf-8") as f:
    content = f.read()

target = '<h2 class="h5 fw-bold mb-0">Hóa Đơn Trong Ca</h2>'
replacement = '''<h2 class="h5 fw-bold mb-0 d-flex align-items-center gap-2">
                                    Hóa Đơn Trong Ca
                                    <span id="pos-sse-status-badge" class="badge bg-success-subtle text-success border border-success-subtle d-inline-flex align-items-center gap-1" style="font-size: 0.7rem; font-weight: 500;">
                                        <span class="spinner-grow spinner-grow-sm text-success" style="width:6px;height:6px;" role="status"></span> Real-time SSE
                                    </span>
                                </h2>'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open("frontend/pos.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: frontend/pos.html updated!")
else:
    print("ERROR: target not found in frontend/pos.html")
