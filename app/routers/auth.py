from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter.depends import RateLimiter
import jwt
from datetime import datetime, timezone

import app.cache
from app.config import settings
from app.oauth2 import oauth2_scheme
from app.database import get_db_session
from app import crud, utils, oauth2

router = APIRouter(tags=["Authentication Matrix"])

@router.post(
    "/login",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session)
):
    user = await crud.get_user_by_email(session, email=user_credentials.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    if not utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    # JWT contains only 'sub' – no role embedding
    access_token = oauth2.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"} # nosec B105


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def logout(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        now = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - now)  # type: ignore

        if ttl > 0:
            await app.cache.redis_client.set(f"blacklist:{jti}", "true", ex=ttl)
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token.")
    except Exception:
        raise HTTPException(status_code=503, detail="Token revocation service unavailable.")

    return {"message": "Successfully logged out. Token mathematically neutralized."}