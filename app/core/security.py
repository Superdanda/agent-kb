import hmac
import hashlib
import base64
from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a valid Fernet key from SECRET_KEY using SHA-256."""
    key_bytes = settings.SECRET_KEY.encode() if settings.SECRET_KEY else b"default-dev-key-change-in-production"
    # Use SHA-256 to derive a 32-byte key, then base64url encode for Fernet
    derived = hashlib.sha256(key_bytes).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


_fernet = _get_fernet()


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_signature(
    secret_key: str,
    method: str,
    path: str,
    query: str,
    timestamp: str,
    nonce: str,
    content_sha256: str,
) -> str:
    string_to_sign = (
        f"{method}\n"
        f"{path}\n"
        f"{query}\n"
        f"{timestamp}\n"
        f"{nonce}\n"
        f"{content_sha256}"
    )
    signature = hmac.new(
        secret_key.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature


def verify_signature(
    secret_key: str,
    method: str,
    path: str,
    query: str,
    timestamp: str,
    nonce: str,
    content_sha256: str,
    signature: str,
) -> bool:
    expected = compute_signature(
        secret_key=secret_key,
        method=method,
        path=path,
        query=query,
        timestamp=timestamp,
        nonce=nonce,
        content_sha256=content_sha256,
    )
    return hmac.compare_digest(expected, signature)
