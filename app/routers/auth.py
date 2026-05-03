# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app import crud, utils, oauth2

router = APIRouter(tags=["Authentication Matrix"])

@router.post("/login")
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