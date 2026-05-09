from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi_limiter.depends import RateLimiter
import uuid

from app.database import get_db_session
from app.schemas import UserCreate, UserRead, RoleCreate, RoleRead, UserInvite
from app import crud
from app.oauth2 import RoleChecker
from app.config import settings

router = APIRouter(prefix="/v1/identity", tags=["Identity & Access Management"])

require_admin = RoleChecker(["System Admin"])

@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin), Depends(RateLimiter(times=5, seconds=60))],
)
async def create_rbac_role(role: RoleCreate, session: AsyncSession = Depends(get_db_session)):
    existing_role = await crud.get_role_by_name(session, role.name)
    if existing_role:
        raise HTTPException(status_code=400, detail="Role identifier already exists.")
    return await crud.create_role(session, role)


@router.post(
    "/invite",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin), Depends(RateLimiter(times=5, seconds=60))],
)
async def invite_user(
    invite: UserInvite,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        activation_jti, user_email = await crud.create_invited_user(session, invite)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build the full activation link using APP_BASE_URL
    activation_url = f"{settings.APP_BASE_URL}/v1/identity/activate?token={activation_jti}"

    return {
        "message": "User invited. Share this link securely.",
        "activation_url": activation_url,
    }


@router.post(
    "/activate",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(times=3, seconds=60))],
)
async def activate_account(
    token: str,
    password: str = Depends(UserCreate.password), # type: ignore # reuse password validation
    session: AsyncSession = Depends(get_db_session)
):
    """New user sets their password and activates the account."""
    success = await crud.activate_user(session, token, password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired activation token.")
    return {"message": "Account activated successfully."}


# @router.post(
#     "/users",
#     response_model=UserRead,
#     status_code=status.HTTP_201_CREATED,
#     dependencies=[Depends(RateLimiter(times=5, seconds=60))],
# )
# async def register_user(user: UserCreate, session: AsyncSession = Depends(get_db_session)):
#     # Legacy self‑registration (still allows direct password)
#     try:
#         new_user = await crud.create_user(session, user)
#         return new_user
#     except IntegrityError:
#         await session.rollback()
#         raise HTTPException(status_code=409, detail="Identity already exists.")