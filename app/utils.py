import bcrypt

def hash_password(password: str) -> str:
    """
    Consumes a raw text password, encodes to bytes, and returns a secure bcrypt hash string.
    """
    # 1. Convert string to bytes
    pwd_bytes = password.encode('utf-8')
    
    # 2. Generate a secure salt and hash
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    
    # 3. Decode back to string for database storage (VARCHAR)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies an incoming password attempt against the database hash.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    
    # bcrypt.checkpw securely compares the raw bytes against the hash in constant time
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)