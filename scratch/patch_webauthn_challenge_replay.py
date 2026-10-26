with open("backend/services/webauthn_verifier.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """    # 1. Kiểm tra Challenge hợp lệ
    if user.current_challenge and user.current_challenge != challenge_used:
        return {
            "verified": False,
            "message": "Challenge sinh trắc học không hợp lệ hoặc đã hết hạn.",
            "is_demo": is_demo_mode,
            "biometric_verified": False
        }"""

replacement = """    # 1. Kiểm tra Challenge hợp lệ (Chống tuyệt đối Replay Attack)
    if not user.current_challenge:
        return {
            "verified": False,
            "message": "Challenge sinh trắc học không tồn tại hoặc đã được sử dụng trước đó (Phát hiện Replay Attack).",
            "is_demo": is_demo_mode,
            "biometric_verified": False
        }

    if user.current_challenge != challenge_used:
        return {
            "verified": False,
            "message": "Challenge sinh trắc học không hợp lệ hoặc đã hết hạn.",
            "is_demo": is_demo_mode,
            "biometric_verified": False
        }"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open("backend/services/webauthn_verifier.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: webauthn_verifier.py fixed with anti-replay challenge check!")
else:
    print("Warning: target not found")
