with open("frontend/js/reconciliation.js", "r", encoding="utf-8") as f:
    content = f.read()

target = """                    credential_id: webauthnProof.credential_id,
                    challenge_used: webauthnProof.challenge_used,
                    assertion_signature: webauthnProof.assertion_signature"""

replacement = """                    credential_id: webauthnProof.credential_id,
                    challenge_used: webauthnProof.challenge_used,
                    assertion_signature: webauthnProof.assertion_signature,
                    client_data_json: webauthnProof.client_data_json,
                    authenticator_data: webauthnProof.authenticator_data"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open("frontend/js/reconciliation.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: Updated manual match WebAuthn payload in reconciliation.js!")
else:
    print("Warning: target not found in reconciliation.js")
