import json
from sqlalchemy.types import TypeDecorator, Text
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import settings
from app.logger import logger

# Load all key versions
try:
    encryption_keys_raw = getattr(settings, "ENCRYPTION_KEYS", None)
    if encryption_keys_raw:
        if isinstance(encryption_keys_raw, str):
            KEYS = json.loads(encryption_keys_raw)
        else:
            KEYS = encryption_keys_raw
    else:
        # Fallback to single key as version "1"
        KEYS = {"1": settings.ENCRYPTION_KEY}
except Exception:
    logger.critical("Failed to parse ENCRYPTION_KEYS, falling back to single key")
    KEYS = {"1": settings.ENCRYPTION_KEY}

CURRENT_KEY_VERSION = str(getattr(settings, "ENCRYPTION_KEY_CURRENT_VERSION", 1))
# Ensure the current version exists
if CURRENT_KEY_VERSION not in KEYS:
    raise RuntimeError(f"Encryption key version {CURRENT_KEY_VERSION} not found")

fernet_instances = {version: Fernet(key.encode()) for version, key in KEYS.items()}


class EncryptedString(TypeDecorator):
    """
    Transparent encryption with key versioning.
    Stored format: "v{version}:{encrypted_base64}"
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            fernet = fernet_instances[CURRENT_KEY_VERSION]
            encrypted = fernet.encrypt(value.encode('utf-8')).decode('utf-8')
            return f"v{CURRENT_KEY_VERSION}:{encrypted}"
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                # Parse version prefix
                version_str, _, ciphertext = value.partition(":")
                version_str = version_str.lstrip("v")
                if version_str not in fernet_instances:
                    raise ValueError(f"Unknown key version: {version_str}")
                fernet = fernet_instances[version_str]
                return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
            except (InvalidToken, ValueError):
                logger.critical("Data integrity failure: Invalid decryption token or unknown key version.")
                raise ValueError("Corrupt or tampered encrypted data found in database.")
        return value