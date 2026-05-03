# app/oauth2.py
import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

def create_access_token(data: dict) -> str:
    """
    Forges a cryptographically signed JSON Web Token.
    """
    to_encode = data.copy()
    
    # Strictly enforce expiration. Immortal tokens are a catastrophic security flaw.
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Sign the token using the HS256 algorithm and your secret key
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt