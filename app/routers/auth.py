# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter.depends import RateLimiter
import jwt
from datetime import datetime, timezone

from app.cache import redis_client
from app.config import settings
from app.oauth2 import oauth2_scheme
from app.database import get_db_session
from app import crud, utils, oauth2

router = APIRouter(tags=["Authentication Matrix"])

@router.post(
    "/login",
    # THE SHIELD: Max 5 requests per 60 seconds per IP
    dependencies=[Depends(RateLimiter(times=5, seconds=60))] # type: ignore
)
async def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(), 
    session: AsyncSession = Depends(get_db_session)
):
    """
    OAuth2 strictly mandates form-data (username/password), not JSON.
    We map OAuth2's 'username' field to our 'email' column.
    """
    # 1. Fetch the identity vector
    user = await crud.get_user_by_email(session, email=user_credentials.username)
    
    # 2. Brutal, ambiguous rejection to prevent enumeration
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
        
    # 3. Cryptographic verification
    if not utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
        
    # 4. Forge the Zero-Trust Payload
    # We embed the user's UUID and strict Role Name into the token.
    access_token = oauth2.create_access_token(
        data={"sub": str(user.id), "role": user.role.name}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(token: str = Depends(oauth2_scheme)):
    """
    The Kill-Switch. Adds the token's JTI to the Redis blacklist.
    """
    try:
        # Decode without verifying expiration (we just need the JTI and EXP)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        # Calculate remaining life of the token
        now = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - now) # type: ignore
        
        if ttl > 0:
            # Slam it into the Redis Blacklist with an automatic self-destruct timer
            await redis_client.set(f"blacklist:{jti}", "true", ex=ttl)
            
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token.")

    return {"message": "Successfully logged out. Token mathematically neutralized."}