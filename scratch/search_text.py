import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("frontend/reconciliation.html", "r", encoding="utf-8") as f:
    html = f.read()

for i, line in enumerate(html.splitlines()):
    if "ghép đơn" in line.lower() or "chờ ghép" in line.lower():
        print(f"HTML Line {i+1}: {line}")

with open("frontend/js/reconciliation.js", "r", encoding="utf-8") as f:
    js = f.read()

for i, line in enumerate(js.splitlines()):
    if "ghép đơn" in line.lower() or "chờ ghép" in line.lower():
        print(f"JS Line {i+1}: {line}")
