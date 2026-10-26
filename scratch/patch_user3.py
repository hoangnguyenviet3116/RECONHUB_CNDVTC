with open("scratch/test_stage2_blockchain_merkle_biometrics.py", "r", encoding="utf-8") as f:
    code = f.read()

target = "test_user = db.query(models.User).filter(models.User.id == 1).first()"
replacement = "test_user = db.query(models.User).filter(models.User.id == 3).first()"

if target in code:
    code = code.replace(target, replacement, 1)
    with open("scratch/test_stage2_blockchain_merkle_biometrics.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: test_stage2_blockchain_merkle_biometrics.py updated to user 3 (OWNER)!")
else:
    print("Warning: target not found")
