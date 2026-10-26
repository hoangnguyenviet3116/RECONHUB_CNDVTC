import base64
import json
import hashlib
import secrets
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key

def test_full_webauthn_flow():
    # 1. Setup simulated user with ECDSA P-256 Key
    priv_key = ec.generate_private_key(ec.SECP256R1())
    pub_key_pem = priv_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
    
    # 2. Challenge generation
    challenge = secrets.token_hex(32)
    
    # 3. ClientDataJSON
    cdata_dict = {
        "type": "webauthn.get",
        "challenge": challenge,
        "origin": "http://localhost:8000"
    }
    cdata_bytes = json.dumps(cdata_dict).encode("utf-8")
    cdata_b64 = base64.b64encode(cdata_bytes).decode("utf-8")
    
    # 4. AuthenticatorData with UV (0x04) and UP (0x01) -> 0x05
    rp_id_hash = hashlib.sha256(b"localhost").digest()
    flags = bytes([0x05]) # UP + UV
    sign_count = (10).to_bytes(4, byteorder="big")
    auth_data_bytes = rp_id_hash + flags + sign_count
    auth_data_b64 = base64.b64encode(auth_data_bytes).decode("utf-8")
    
    # 5. Sign with private key
    signed_payload = auth_data_bytes + hashlib.sha256(cdata_bytes).digest()
    sig_bytes = priv_key.sign(signed_payload, ec.ECDSA(hashes.SHA256()))
    sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
    
    # 6. Verify with our planned function logic
    def verify(pubkey_pem, chall_expected, cdata_in, adata_in, sig_in):
        cdata_raw = base64.b64decode(cdata_in)
        adata_raw = base64.b64decode(adata_in)
        sig_raw = base64.b64decode(sig_in)
        
        cdata_parsed = json.loads(cdata_raw.decode("utf-8"))
        if cdata_parsed.get("type") != "webauthn.get":
            return False, "Invalid type"
        if cdata_parsed.get("challenge") != chall_expected:
            return False, "Challenge mismatch"
            
        if len(adata_raw) < 37:
            return False, "Authenticator data too short"
        flag = adata_raw[32]
        if not (flag & 0x04): # UV bit
            return False, "Biometric UV bit not set"
            
        pk = load_pem_public_key(pubkey_pem.encode("utf-8"))
        to_verify = adata_raw + hashlib.sha256(cdata_raw).digest()
        pk.verify(sig_raw, to_verify, ec.ECDSA(hashes.SHA256()))
        return True, "FIDO2 ECDSA P-256 and Biometric UV Flag verified!"

    ok, msg = verify(pub_key_pem, challenge, cdata_b64, auth_data_b64, sig_b64)
    print(f"WebAuthn flow test: {ok} - {msg}")
    assert ok is True
    
    # Test failure if UV bit is not set (e.g. flag = 0x01 only UP, no UV)
    auth_data_no_uv = rp_id_hash + bytes([0x01]) + sign_count
    auth_data_no_uv_b64 = base64.b64encode(auth_data_no_uv).decode("utf-8")
    sig_no_uv = base64.b64encode(priv_key.sign(auth_data_no_uv + hashlib.sha256(cdata_bytes).digest(), ec.ECDSA(hashes.SHA256()))).decode("utf-8")
    
    ok_fail, msg_fail = verify(pub_key_pem, challenge, cdata_b64, auth_data_no_uv_b64, sig_no_uv)
    print(f"No UV flag test: {ok_fail} - {msg_fail}")
    assert ok_fail is False
    assert "UV bit not set" in msg_fail
    print("All WebAuthn FIDO2 verification scenarios passed successfully!")

test_full_webauthn_flow()
