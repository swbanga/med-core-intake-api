import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app import crud, schemas

# THIS TRIGGER: Tells Swagger UI to look for a token at the /login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: AsyncSession = Depends(get_db_session)
):
    """
    The Interrogator. Extracts the token, verifies the cryptographic signature,
    ensures it is not expired, and fetches the user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decode the JWT payload
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub") # type: ignore
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        # Intercept expired tokens cleanly
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.PyJWTError:
        # Catch all other cryptographic failures (tampering, bad signature)
        raise credentials_exception

    # 2. Verify the identity vector still exists in the database
    user = await crud.get_user_by_id(session, user_id=user_id) # WE NEED TO ADD THIS TO CRUD
    if user is None:
        raise credentials_exception
        
    # 3. Check the kill-switch
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
        
    return user

class RoleChecker:
    """
    The Authorization Matrix. Evaluates if the authenticated user has the required role.
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: schemas.UserRead = Depends(get_current_user)):
        if user.role.name not in self.allowed_roles: # type: ignore
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted. Insufficient RBAC clearance."
            )
        return user