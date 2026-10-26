with open("frontend/js/reconciliation.js", "r", encoding="utf-8") as f:
    content = f.read()

# Place 1: OVERPAYMENT_RESOLUTION (around line 387)
p1_old = """                credential_id: webauthnProof.credential_id,
                challenge_used: webauthnProof.challenge_used,
                assertion_signature: webauthnProof.assertion_signature"""

p1_new = """                credential_id: webauthnProof.credential_id,
                challenge_used: webauthnProof.challenge_used,
                assertion_signature: webauthnProof.assertion_signature,
                client_data_json: webauthnProof.client_data_json,
                authenticator_data: webauthnProof.authenticator_data"""

# Replace all occurrences where credential_id, challenge_used, assertion_signature are sent
if p1_old in content:
    count = content.count(p1_old)
    content = content.replace(p1_old, p1_new)
    with open("frontend/js/reconciliation.js", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"SUCCESS: Updated {count} occurrences in frontend/js/reconciliation.js with client_data_json & authenticator_data!")
else:
    print("Warning: p1_old pattern not found in reconciliation.js")
