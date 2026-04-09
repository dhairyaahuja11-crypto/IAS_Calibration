import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv


MODEL_KEY_ENV_VAR = "MODEL_ENCRYPTION_KEY"
MAGIC_HEADER = b"AGNEXTPRO1"
SALT_SIZE = 16
NONCE_SIZE = 12
PBKDF2_ITERATIONS = 100_000
AES_KEY_SIZE = 16  # AES-128


def _normalize_key(raw_key: str) -> str:
    key = (raw_key or "").strip()
    if not key:
        raise ValueError(
            f"{MODEL_KEY_ENV_VAR} was not found. Add it to your .env file before exporting models."
        )
    if len(key) < 8:
        raise ValueError(
            f"{MODEL_KEY_ENV_VAR} must be at least 8 characters long."
        )
    return key


def get_default_encryption_key() -> str:
    load_dotenv()
    return _normalize_key(os.getenv(MODEL_KEY_ENV_VAR, ""))


def _derive_aes_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_model_payload(payload: dict, passphrase: str) -> bytes:
    normalized_key = _normalize_key(passphrase)
    plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    aes_key = _derive_aes_key(normalized_key, salt)
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, None)
    return MAGIC_HEADER + salt + nonce + ciphertext


def decrypt_model_payload(blob: bytes, passphrase: str) -> dict:
    normalized_key = _normalize_key(passphrase)
    if len(blob) <= len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE:
        raise ValueError("Encrypted model file is too short or corrupted.")
    if not blob.startswith(MAGIC_HEADER):
        raise ValueError("Unsupported encrypted model format.")

    offset = len(MAGIC_HEADER)
    salt = blob[offset:offset + SALT_SIZE]
    offset += SALT_SIZE
    nonce = blob[offset:offset + NONCE_SIZE]
    offset += NONCE_SIZE
    ciphertext = blob[offset:]

    aes_key = _derive_aes_key(normalized_key, salt)
    try:
        plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise ValueError(
            "Failed to decrypt model. The encryption key may be wrong, or the file may be corrupted."
        ) from exc

    try:
        return json.loads(plaintext.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Decrypted model payload is not valid JSON.") from exc


def save_encrypted_model(path: str | Path, payload: dict, passphrase: str) -> Path:
    target = Path(path)
    target.write_bytes(encrypt_model_payload(payload, passphrase))
    return target


def load_encrypted_model(path: str | Path, passphrase: str) -> dict:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Encrypted model file not found: {target}")
    return decrypt_model_payload(target.read_bytes(), passphrase)
