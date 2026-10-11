import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from dotenv import load_dotenv

load_dotenv()

KEY_ID = "v1"


def _master_key() -> bytes:
    raw = os.getenv("MASTER_KEY")
    if not raw:
        raise RuntimeError("MASTER_KEY is not set in .env")
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("MASTER_KEY must be 32 bytes, base64-encoded")
    return key


def get_dek(user_id: str) -> bytes:
    """Return a 32-byte per-user key derived from the master key with HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"aldr/email-dek/v1|" + str(user_id).encode("utf-8"),
    )
    return hkdf.derive(_master_key())


def encrypt_email(payload: dict, user_id: str, provider_id: str) -> tuple[bytes, bytes, str]:
    """Encrypt the sensitive email fields. Returns (ciphertext, nonce, key_id)."""
    dek = get_dek(user_id)
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    nonce = os.urandom(12)
    aad = f"{user_id}|{provider_id}".encode("utf-8")
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext, aad)
    return ciphertext, nonce, KEY_ID


def decrypt_email(ciphertext: bytes, nonce: bytes, user_id: str, provider_id: str) -> dict:
    dek = get_dek(user_id)
    aad = f"{user_id}|{provider_id}".encode("utf-8")
    plaintext = AESGCM(dek).decrypt(nonce, ciphertext, aad)   
    return json.loads(plaintext.decode("utf-8"))