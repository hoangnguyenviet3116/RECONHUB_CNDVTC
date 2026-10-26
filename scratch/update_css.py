# -*- coding: utf-8 -*-
with open('frontend/css/styles.css', 'r', encoding='utf-8') as f:
    c = f.read()

target = """.btn-fp-success:hover {
    background: linear-gradient(135deg, #047857 0%, #065f46 100%);
    color: #ffffff;
    transform: translateY(-1px);
}"""

replacement = """.btn-fp-success:hover {
    background: linear-gradient(135deg, #047857 0%, #065f46 100%);
    color: #ffffff;
    transform: translateY(-1px);
}

.btn-fp-danger {
    background: linear-gradient(135deg, #e11d48 0%, #be123c 100%);
    color: #ffffff;
    border: 1px solid #be123c;
    border-radius: var(--fp-radius-sm);
    padding: 0.6rem 1.25rem;
    font-size: 0.88rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    text-decoration: none;
    box-shadow: 0 4px 12px rgba(225, 29, 72, 0.2);
    transition: all 0.2s ease;
}

.btn-fp-danger:hover {
    background: linear-gradient(135deg, #be123c 0%, #9f1239 100%);
    color: #ffffff;
    transform: translateY(-1px);
}"""

assert target in c, "target not found in styles.css"
c = c.replace(target, replacement, 1)

with open('frontend/css/styles.css', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated frontend/css/styles.css successfully")
