from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import uuid
from fastapi import HTTPException

from app.models import PatientProfileHistory
from app.schemas import PatientProfileUpdate
from app.models import User, Role, PatientProfile
from app.schemas import UserCreate, RoleCreate, PatientProfileCreate
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

async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Fetches a user by UUID. Required for JWT token validation."""
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    return result.scalars().first()

# ==========================================
# PATIENT PROFILE (PHI) DATA ACCESS
# ==========================================
async def create_patient_profile(session: AsyncSession, profile: PatientProfileCreate, user_id: str) -> PatientProfile:
    """Injects PHI into the vault. Anchors to the JWT user_id."""
    db_profile = PatientProfile(
        **profile.model_dump(), 
        user_id=uuid.UUID(user_id) # Hard-anchored here. Client cannot spoof this.
    )
    session.add(db_profile)
    await session.commit()
    await session.refresh(db_profile)
    return db_profile

async def get_patient_profile_by_user(session: AsyncSession, user_id: str) -> PatientProfile | None:
    """Fetches a profile exclusively by the authenticated user's ID."""
    stmt = select(PatientProfile).where(PatientProfile.user_id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    return result.scalars().first()

async def get_all_patient_profiles(
    session: AsyncSession, 
    limit: int = 100, 
    offset: int = 0
) -> list[PatientProfile]:
    """
    Fetches a paginated list of PHI. 
    Never executed without strict Medical/Admin clearance.
    """
    # Math: Limit bounds the size, Offset skips previous pages
    stmt = select(PatientProfile).limit(limit).offset(offset)
    result = await session.execute(stmt)
    
    # .all() is safe here because the .limit() constrained the SQL engine
    return list(result.scalars().all())


async def update_patient_profile(
    session: AsyncSession, 
    profile_id: str, 
    update_data: PatientProfileUpdate, 
    actor_id: str
) -> PatientProfile:
    """Updates a profile and enforces the immutable audit trail."""
    
    # 1. Fetch the current state
    stmt = select(PatientProfile).where(PatientProfile.id == uuid.UUID(profile_id))
    result = await session.execute(stmt)
    db_profile = result.scalars().first()
    
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    # 2. Forge the Historical Snapshot
    history_record = PatientProfileHistory(
        profile_id=db_profile.id,
        changed_by_user_id=uuid.UUID(actor_id),
        old_first_name=db_profile.first_name,
        old_last_name=db_profile.last_name,
        old_date_of_birth=db_profile.date_of_birth,
        old_medical_history=db_profile.medical_history
    )
    session.add(history_record)

    # 3. Apply the Updates dynamically
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_profile, key, value)

    # 4. Commit the Atomic Transaction (Both succeed or both fail)
    await session.commit()
    await session.refresh(db_profile)
    
    return db_profile