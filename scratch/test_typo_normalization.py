import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import re
from rapidfuzz import fuzz

def normalize_typo_order_code(raw_token: str) -> list[str]:
    """
    Substitutes optical typos (O->0, I/L->1, B->8, S->5, Z->2) in code numbers.
    """
    token = raw_token.strip().upper()
    variants = [token]
    
    # If token starts with ORD / HD / DH, extract the suffix
    m = re.match(r'^(ORD|HD|DH|DON|BILL)?\s*([0-9A-Z]+)$', token)
    if m:
        prefix, suffix = m.groups()
        # Substitution map
        trans_table = str.maketrans({
            'O': '0', 'Q': '0',
            'I': '1', 'L': '1',
            'B': '8',
            'S': '5',
            'Z': '2'
        })
        corrected_suffix = suffix.translate(trans_table)
        variants.append(f"ORD{corrected_suffix}")
        variants.append(f"ORD{suffix}")
        variants.append(corrected_suffix)
        
    return list(dict.fromkeys(variants))

def extract_tier1_candidate_codes(content: str) -> list[str]:
    clean = (content or "").upper()
    # Normalize punctuation
    for ch in [",", ".", ";", ":", "-", "_", "/"]:
        clean = clean.replace(ch, " ")
        
    # Match patterns like ORD 1001, ORD1001, ORD 1OO1, etc.
    tokens = clean.split()
    candidates = []
    
    # 1. Direct tokens
    for i, t in enumerate(tokens):
        if t in ["ORD", "HD", "DH", "DON", "BILL"] and i + 1 < len(tokens):
            combined = f"ORD{tokens[i+1]}"
            candidates.extend(normalize_typo_order_code(combined))
        elif t.startswith("ORD") or t.startswith("HD") or t.startswith("DH"):
            candidates.extend(normalize_typo_order_code(t))
        elif t.isdigit() and len(t) >= 4:
            candidates.append(f"ORD{t}")
            
    return list(dict.fromkeys(candidates))

# Tests
test_cases = [
    "TT ORD 1001 CHUYEN TIEN",
    "ORD-1001",
    "ORD_1OO1", # with O
    "TT ORD1001 VA ORD1002",
    "TT DON 1001",
    "CHUYEN KHOAN BILL 1O01",
    "ORDIOOI",
]

for tc in test_cases:
    cands = extract_tier1_candidate_codes(tc)
    print(f"Content: '{tc}' -> Candidates: {cands}")

print("RapidFuzz version and sample similarity:")
sim = fuzz.token_sort_ratio("TT ORD1001 THANH TOAN", "ORD1001")
print(f"Fuzz similarity: {sim}")
