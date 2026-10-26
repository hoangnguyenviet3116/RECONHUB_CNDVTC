with open("backend/routers/mock_bank.py", "r", encoding="utf-8") as f:
    code = f.read()

code_norm = code.replace("\r\n", "\n")

target_signing = """    if is_invalid_hmac:
        signature = "INVALID_TAMPERED_HMAC_SIGNATURE_0000000000000000"
    else:
        signature = generate_hmac_signature(payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "x-hub-signature": signature
    }"""

replacement_signing = """    import time
    now_ts = time.time()
    if test_mode == "REPLAY_ATTACK" or payload.get("simulate_replay") is True:
        # Giả lập bản tin cũ quá hạn (600s trước > 300s tolerance)
        ts_str = str(now_ts - 600)
    else:
        ts_str = str(now_ts)

    if is_invalid_hmac:
        signature = "INVALID_TAMPERED_HMAC_SIGNATURE_0000000000000000"
    else:
        signature = generate_hmac_signature(payload_bytes, timestamp=ts_str)

    headers = {
        "Content-Type": "application/json",
        "x-hub-signature": signature,
        "x-hub-timestamp": ts_str
    }"""

assert target_signing in code_norm, "target_signing not found in mock_bank.py"
code_norm = code_norm.replace(target_signing, replacement_signing)

if "\r\n" in code:
    code_norm = code_norm.replace("\n", "\r\n")

with open("backend/routers/mock_bank.py", "w", encoding="utf-8") as f:
    f.write(code_norm)

print("SUCCESS: backend/routers/mock_bank.py updated with timestamp header & replay testing")
