with open('backend/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """class DecisionType(str, enum.Enum):
    APPROVE_MANUAL_MATCH = 'APPROVE_MANUAL_MATCH'
    REVERSE_ALLOCATION = 'REVERSE_ALLOCATION'
    REQUEST_INFO = 'REQUEST_INFO'
    REJECT_TX = 'REJECT_TX'"""

replacement = """class DecisionType(str, enum.Enum):
    APPROVE_MANUAL_MATCH = 'APPROVE_MANUAL_MATCH'
    REVERSE_ALLOCATION = 'REVERSE_ALLOCATION'
    REQUEST_INFO = 'REQUEST_INFO'
    REJECT_TX = 'REJECT_TX'
    OVERPAYMENT_RESOLUTION = 'OVERPAYMENT_RESOLUTION'"""

content_norm = content.replace('\r\n', '\n')
assert target in content_norm, "Target not found in models.py"
content_norm = content_norm.replace(target, replacement)
if '\r\n' in content:
    content_norm = content_norm.replace('\n', '\r\n')

with open('backend/models.py', 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("SUCCESS: backend/models.py updated")
