import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from decimal import Decimal
from typing import List, Tuple

def find_subset_sum_combinations(candidates: List[Tuple[int, Decimal]], target: Decimal, max_subsets: int = 5) -> List[List[int]]:
    """
    candidates: list of (order_id, remaining_amount)
    target: target amount to match
    Returns list of subsets (each subset is list of order_ids) that exactly sum to target.
    Pruned with branch-and-bound.
    """
    # Filter out orders with remaining > target or <= 0
    valid_candidates = [(oid, amt) for oid, amt in candidates if Decimal("0.00") < amt <= target]
    # Sort descending by amount for efficient pruning
    valid_candidates.sort(key=lambda x: x[1], reverse=True)
    
    solutions = []
    
    def backtrack(start_idx: int, current_sum: Decimal, current_path: List[int]):
        nonlocal solutions
        if len(solutions) >= max_subsets:
            return
            
        if current_sum == target:
            solutions.append(list(current_path))
            return
            
        for i in range(start_idx, len(valid_candidates)):
            oid, amt = valid_candidates[i]
            if current_sum + amt > target:
                continue
                
            current_path.append(oid)
            backtrack(i + 1, current_sum + amt, current_path)
            current_path.pop()
            
    backtrack(0, Decimal("0.00"), [])
    return solutions

# Test cases
orders = [
    (101, Decimal("30000.00")),
    (102, Decimal("50000.00")),
    (103, Decimal("45000.00")),
    (104, Decimal("25000.00")),
]

# Target 80,000 -> 30k + 50k (one solution)
res1 = find_subset_sum_combinations(orders, Decimal("80000.00"))
print(f"Target 80k solutions: {res1}")
assert res1 == [[102, 101]]

# Target 75,000 -> 50k + 25k or 30k + 45k (two solutions -> ambiguous)
res2 = find_subset_sum_combinations(orders, Decimal("75000.00"))
print(f"Target 75k solutions (ambiguous): {res2}")
assert len(res2) == 2

print("Subset-Sum logic verified successfully!")
