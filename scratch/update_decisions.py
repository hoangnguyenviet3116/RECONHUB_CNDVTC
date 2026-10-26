with open("backend/routers/decisions.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """    challenge_used = decision_data.get("challenge_used") or decision_data.get("challenge")
    assertion_signature = decision_data.get("assertion_signature") or decision_data.get("signature")
    credential_id = decision_data.get("credential_id")
    is_demo = decision_data.get("is_demo", True)
    security_mode = decision_data.get("security_mode")

    auth_result = verify_webauthn_assertion(
        db=db,
        user=user,
        challenge_used=challenge_used,
        assertion_signature=assertion_signature,
        credential_id=credential_id,
        is_demo_mode=is_demo,
        security_mode=security_mode
    )"""

replacement = """    challenge_used = decision_data.get("challenge_used") or decision_data.get("challenge")
    assertion_signature = decision_data.get("assertion_signature") or decision_data.get("signature")
    credential_id = decision_data.get("credential_id")
    client_data_json = decision_data.get("client_data_json") or decision_data.get("clientDataJSON")
    authenticator_data = decision_data.get("authenticator_data") or decision_data.get("authenticatorData")
    is_demo = decision_data.get("is_demo", True)
    security_mode = decision_data.get("security_mode")

    auth_result = verify_webauthn_assertion(
        db=db,
        user=user,
        challenge_used=challenge_used,
        assertion_signature=assertion_signature,
        credential_id=credential_id,
        client_data_json=client_data_json,
        authenticator_data=authenticator_data,
        is_demo_mode=is_demo,
        security_mode=security_mode
    )"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open("backend/routers/decisions.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: backend/routers/decisions.py updated with WebAuthn clientDataJSON & authenticatorData!")
else:
    print("ERROR: target not found in decisions.py")
