# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db_session
from app.schemas import UserCreate, UserRead, RoleCreate, RoleRead
from app import crud

# The router instance. Tags group these endpoints in the Swagger UI.
router = APIRouter(prefix="/v1/identity", tags=["Identity & Access Management"])

@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_rbac_role(role: RoleCreate, session: AsyncSession = Depends(get_db_session)):
    """Creates a new Role in the authorization matrix."""
    existing_role = await crud.get_role_by_name(session, role.name)
    if existing_role:
        raise HTTPException(status_code=400, detail="Role identifier already exists.")
    
    return await crud.create_role(session, role)

@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, session: AsyncSession = Depends(get_db_session)):
    """Registers a new user, hashes password, and anchors them to a role."""
    try:
        new_user = await crud.create_user(session, user)
        return new_user
    except IntegrityError:
        # Intercepts database-level unique constraint violations (e.g., duplicate email)
        await session.rollback()
        raise HTTPException(status_code=400, detail="Email already registered or Role ID invalid.")