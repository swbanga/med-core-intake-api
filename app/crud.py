from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import uuid

from app.models import User, Role
from app.schemas import UserCreate, RoleCreate
from app.utils import hash_password

# ==========================================
# ROLE DATA ACCESS
# ==========================================
async def get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    """Fetches a role by its strict string identifier."""
    stmt = select(Role).where(Role.name == name)
    result = await session.execute(stmt)
    return result.scalars().first()

async def create_role(session: AsyncSession, role: RoleCreate) -> Role:
    """Inserts a new RBAC role into the matrix."""
    db_role = Role(name=role.name, description=role.description)
    session.add(db_role)
    await session.commit()
    await session.refresh(db_role)
    return db_role

# ==========================================
# USER DATA ACCESS
# ==========================================
async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetches a user. Critical for the authentication flow."""
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    # The 'joinedload' we set in models.py ensures the User.role is fetched here asynchronously
    return result.scalars().first()

async def create_user(session: AsyncSession, user: UserCreate) -> User:
    """
    Consumes a Pydantic UserCreate DTO, hashes the password, 
    and commits the User model to the database.
    """
    # 1. Brutal cryptographic enforcement
    hashed_pwd = hash_password(user.password)
    
    # 2. Map DTO to SQLAlchemy Model
    db_user = User(
        email=user.email,
        hashed_password=hashed_pwd,
        role_id=user.role_id,
        is_active=user.is_active
    )
    
    # 3. State execution
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    
    return db_user