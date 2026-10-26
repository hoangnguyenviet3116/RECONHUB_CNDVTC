import hashlib
from typing import List, Tuple, Dict

def hash_pair(left: str, right: str) -> str:
    raw = f"{left}{right}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def build_merkle_tree(leaf_hashes: List[str]) -> Tuple[str, List[List[str]]]:
    if not leaf_hashes:
        empty_root = hashlib.sha256(b"EMPTY_MERKLE_TREE").hexdigest()
        return empty_root, []
        
    current_level = list(leaf_hashes)
    levels = [current_level]
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            if i + 1 < len(current_level):
                right = current_level[i + 1]
            else:
                right = left # duplicate if odd
            next_level.append(hash_pair(left, right))
        levels.append(next_level)
        current_level = next_level
        
    return current_level[0], levels

def get_merkle_proof(leaf_index: int, tree_levels: List[List[str]]) -> List[Dict[str, str]]:
    proof = []
    idx = leaf_index
    for level_idx in range(len(tree_levels) - 1):
        level = tree_levels[level_idx]
        if idx % 2 == 0:
            # Sibling is on the right
            if idx + 1 < len(level):
                sibling = level[idx + 1]
            else:
                sibling = level[idx] # duplicated
            proof.append({"position": "right", "hash": sibling})
        else:
            # Sibling is on the left
            sibling = level[idx - 1]
            proof.append({"position": "left", "hash": sibling})
        idx = idx // 2
    return proof

def verify_merkle_proof(leaf_hash: str, proof: List[Dict[str, str]], expected_root: str) -> bool:
    current = leaf_hash
    for item in proof:
        pos = item["position"]
        sibling = item["hash"]
        if pos == "right":
            current = hash_pair(current, sibling)
        else:
            current = hash_pair(sibling, current)
    return current == expected_root

# Test
leaves = [
    hashlib.sha256(f"ALLOCATION_{i}".encode()).hexdigest() for i in range(5)
]
root, levels = build_merkle_tree(leaves)
print(f"Merkle Root for 5 allocations: {root}")

# Verify each leaf with its proof
for i, leaf in enumerate(leaves):
    proof = get_merkle_proof(i, levels)
    valid = verify_merkle_proof(leaf, proof, root)
    print(f"Leaf {i} proof valid: {valid}")
    assert valid, f"Leaf {i} failed verification!"

# Tamper test: if leaf is tampered
tampered_leaf = hashlib.sha256(b"TAMPERED").hexdigest()
proof_0 = get_merkle_proof(0, levels)
assert not verify_merkle_proof(tampered_leaf, proof_0, root), "Tampered leaf should fail!"
print("Merkle Tree implementation verified successfully!")
