from sqlalchemy.types import TypeDecorator, Text
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import settings
from app.logger import logger

# Initialize the AES cipher suite
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())

class EncryptedString(TypeDecorator):
    """
    Transparently encrypts data writing to the DB, 
    and decrypts data reading from the DB.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Intercepts the INSERT/UPDATE statement."""
        if value is not None:
            # Encrypt the string and decode the bytes to store as Text
            return cipher_suite.encrypt(value.encode('utf-8')).decode('utf-8')
        return value

    def process_result_value(self, value, dialect):
        """Intercepts the SELECT statement."""
        if value is not None:
            try:
                return cipher_suite.decrypt(value.encode('utf-8')).decode('utf-8')
            except InvalidToken:
                # If someone tampered with the raw DB string, or the key changed, we panic loudly.
                logger.critical("Data integrity failure: Invalid decryption token detected.")
                raise ValueError("Corrupt or tampered encrypted data found in database.")
        return value