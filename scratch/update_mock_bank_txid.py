with open("backend/routers/mock_bank.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """        return {
            "status": "triggered",
            "message": resp_data.get("message", "Đã tiếp nhận bản tin ngân hàng và xử lý phân bổ đối soát."),
            "mock_bank_response_code": response.status_code,
            "response_data": resp_data
        }"""

replacement = """        return {
            "status": "triggered",
            "message": resp_data.get("message", "Đã tiếp nhận bản tin ngân hàng và xử lý phân bổ đối soát."),
            "mock_bank_response_code": response.status_code,
            "transaction_id": resp_data.get("transaction_id"),
            "reference_code": resp_data.get("reference_code"),
            "response_data": resp_data
        }"""

if target in code:
    code = code.replace(target, replacement, 1)
    with open("backend/routers/mock_bank.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: mock_bank.py updated with top-level transaction_id!")
else:
    print("Warning: target not found in mock_bank.py")
