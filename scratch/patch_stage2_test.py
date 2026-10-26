with open("scratch/test_stage2_blockchain_merkle_biometrics.py", "r", encoding="utf-8") as f:
    code = f.read()

target = 'tx_id = r_ex_tx.json()["transaction_id"]'
replacement = 'tx_id = r_ex_tx.json().get("transaction_id") or r_ex_tx.json().get("response_data", {}).get("transaction_id")'

if target in code:
    code = code.replace(target, replacement, 1)
    with open("scratch/test_stage2_blockchain_merkle_biometrics.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: test_stage2_blockchain_merkle_biometrics.py updated!")
else:
    print("Warning: target not found")
