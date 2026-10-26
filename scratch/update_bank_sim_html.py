with open("frontend/bank-simulator.html", "r", encoding="utf-8") as f:
    content = f.read()

target = '<option value="CONCURRENT_DUPLICATE">Gửi trùng 2 lần</option>'
replacement = '''<option value="CONCURRENT_DUPLICATE">Gửi trùng 2 lần</option>
                                            <option value="REPLAY_ATTACK">Tấn công phát lại (Replay Attack)</option>'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open("frontend/bank-simulator.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: frontend/bank-simulator.html updated!")
else:
    print("ERROR: target not found in bank-simulator.html")
