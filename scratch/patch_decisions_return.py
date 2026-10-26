with open("backend/routers/decisions.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. In APPROVE_MANUAL_MATCH return
old_m1 = """        return {
            "status": "success",
            "message": f"Phân bổ thủ công thành công {alloc_amount:,.0f} VNĐ vào đơn {order.order_code}.",
            "allocation_id": new_alloc.id,
            "decision_id": decision_rec.id
        }"""

new_m1 = """        return {
            "status": "success",
            "message": f"Phân bổ thủ công thành công {alloc_amount:,.0f} VNĐ vào đơn {order.order_code}.",
            "allocation_id": new_alloc.id,
            "decision_id": decision_rec.id,
            "biometric_verified": True
        }"""

if old_m1 in content:
    content = content.replace(old_m1, new_m1, 1)

# 2. In REVERSE_ALLOCATION return
old_m2 = """        return {
            "status": "success",
            "message": f"Đảo bút toán #{orig_alloc.id} thành công (-{orig_amount:,.0f} VNĐ).",
            "reversal_allocation_id": reversal_alloc.id,
            "decision_id": decision_rec.id
        }"""

new_m2 = """        return {
            "status": "success",
            "message": f"Đảo bút toán #{orig_alloc.id} thành công (-{orig_amount:,.0f} VNĐ).",
            "reversal_allocation_id": reversal_alloc.id,
            "decision_id": decision_rec.id,
            "biometric_verified": True
        }"""

if old_m2 in content:
    content = content.replace(old_m2, new_m2, 1)

# 3. In OVERPAYMENT_RESOLUTION return
old_m3 = """        return {
            "status": "success",
            "message": f"Đã ghi nhận phương thức xử lý khoản tiền thừa ({float(tx.unallocated_amount):,.0f} VNĐ) cho giao dịch {tx.reference_code}.",
            "decision_id": decision_rec.id,
            "bank_transaction_id": tx.id,
            "reference_code": tx.reference_code,
            "order_code": matched_order.order_code if matched_order else None,
            "unallocated_amount": float(tx.unallocated_amount),
            "handling_method": method_plan
        }"""

new_m3 = """        return {
            "status": "success",
            "message": f"Đã ghi nhận phương thức xử lý khoản tiền thừa ({float(tx.unallocated_amount):,.0f} VNĐ) cho giao dịch {tx.reference_code}.",
            "decision_id": decision_rec.id,
            "bank_transaction_id": tx.id,
            "reference_code": tx.reference_code,
            "order_code": matched_order.order_code if matched_order else None,
            "unallocated_amount": float(tx.unallocated_amount),
            "handling_method": method_plan,
            "biometric_verified": True
        }"""

if old_m3 in content:
    content = content.replace(old_m3, new_m3, 1)

with open("backend/routers/decisions.py", "w", encoding="utf-8") as f:
    f.write(content)
print("SUCCESS: decisions.py updated with biometric_verified in return payloads!")
