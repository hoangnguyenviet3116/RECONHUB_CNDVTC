with open("frontend/js/bank_simulator.js", "r", encoding="utf-8") as f:
    content = f.read()

target = """        tamper_signature: testMode === "INVALID_HMAC",
        simulate_invalid_hmac: testMode === "INVALID_HMAC"
    };"""

replacement = """        tamper_signature: testMode === "INVALID_HMAC",
        simulate_invalid_hmac: testMode === "INVALID_HMAC",
        test_mode: testMode,
        simulate_replay_attack: testMode === "REPLAY_ATTACK"
    };"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open("frontend/js/bank_simulator.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: frontend/js/bank_simulator.js updated!")
else:
    print("ERROR: target not found in bank_simulator.js")
