from passlib.context import CryptContext

# Brutal Bcrypt configuration. Do not lower the default rounds.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Consumes a raw text password and returns a secure bcrypt hash."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies an incoming password attempt against the database hash."""
    return pwd_context.verify(plain_password, hashed_password)