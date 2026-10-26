import base64
import json
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# 1. Generate an ECDSA P-256 key pair (representing authenticator hardware like Touch ID / Windows Hello)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()
pubkey_pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")

# 2. Challenge from backend
challenge = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# 3. ClientDataJSON constructed by browser
client_data_dict = {
    "type": "webauthn.get",
    "challenge": challenge,
    "origin": "http://localhost:8000",
    "crossOrigin": False
}
client_data_bytes = json.dumps(client_data_dict).encode("utf-8")
client_data_hash = hashlib.sha256(client_data_bytes).digest()

# 4. AuthenticatorData constructed by Secure Enclave / TPM
# 32 bytes rpIdHash + 1 byte flags + 4 bytes signCount
rp_id_hash = hashlib.sha256(b"localhost").digest() # 32 bytes
# Flags: Bit 0 = UP (User Present: 0x01), Bit 2 = UV (User Verified Biometric: 0x04) -> 0x05
flags = bytes([0x05])
sign_count = (1).to_bytes(4, byteorder="big")
auth_data_bytes = rp_id_hash + flags + sign_count

# Signed data is authenticatorData + sha256(clientDataJSON)
signed_data = auth_data_bytes + client_data_hash

# 5. Signature generated inside biometric chip
signature = private_key.sign(signed_data, ec.ECDSA(hashes.SHA256()))
sig_b64 = base64.b64encode(signature).decode("utf-8")
auth_data_b64 = base64.b64encode(auth_data_bytes).decode("utf-8")
client_data_b64 = base64.b64encode(client_data_bytes).decode("utf-8")

# 6. Verification logic on Backend
def verify_fido2_assertion(pubkey_pem: str, challenge_expected: str, cdata_b64: str, adata_b64: str, sig_b64: str):
    # Decode
    cdata = base64.b64decode(cdata_b64)
    adata = base64.b64decode(adata_b64)
    sig = base64.b64decode(sig_b64)
    
    # 1. Parse clientDataJSON
    cdata_json = json.loads(cdata.decode("utf-8"))
    if cdata_json.get("type") != "webauthn.get":
        return False, "Invalid type in clientDataJSON"
    if cdata_json.get("challenge") != challenge_expected:
        return False, "Challenge mismatch in clientDataJSON"
        
    # 2. Check authenticatorData flags
    if len(adata) < 37:
        return False, "Invalid authenticatorData length"
    flag_byte = adata[32]
    user_present = bool(flag_byte & 0x01)
    user_verified = bool(flag_byte & 0x04) # Biometric verification flag
    
    if not user_present:
        return False, "User not present"
    if not user_verified:
        return False, "User biometric not verified"
        
    # 3. Cryptographic signature check
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    loaded_pubkey = load_pem_public_key(pubkey_pem.encode("utf-8"))
    
    cdata_h = hashlib.sha256(cdata).digest()
    verification_data = adata + cdata_h
    
    try:
        loaded_pubkey.verify(sig, verification_data, ec.ECDSA(hashes.SHA256()))
        return True, "ECDSA P-256 Signature and Biometric UV flag verified successfully!"
    except Exception as e:
        return False, f"Signature verification failed: {e}"

valid, msg = verify_fido2_assertion(pubkey_pem, challenge, client_data_b64, auth_data_b64, sig_b64)
print(f"FIDO2 Verification Result: {valid} - {msg}")
assert valid is True
print("WebAuthn / FIDO2 Public-Key Cryptography verified successfully!")
