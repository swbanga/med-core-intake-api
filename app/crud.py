import uuid
import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.config import settings
from app.models import PatientProfileHistory, User, Role, PatientProfile
from app.schemas import PatientProfileUpdate, UserCreate, RoleCreate, PatientProfileCreate, UserInvite
from app.utils import hash_password

# ==========================================
# ROLE DATA ACCESS
# ==========================================
async def get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    result = await session.execute(stmt)
    return result.scalars().first()

async def create_role(session: AsyncSession, role: RoleCreate) -> Role:
    db_role = Role(name=role.name, description=role.description)
    session.add(db_role)
    await session.commit()
    await session.refresh(db_role)
    return db_role

# ==========================================
# USER DATA ACCESS
# ==========================================
async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalars().first()

async def create_user(session: AsyncSession, user: UserCreate) -> User:
    hashed_pwd = hash_password(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_pwd,
        role_id=user.role_id,
        is_active=True,
        is_password_set=True,
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

async def create_invited_user(session: AsyncSession, invite: UserInvite) -> tuple[str, str]:
    # Resolve role name to ID
    stmt = select(Role).where(Role.name == invite.role_name)
    result = await session.execute(stmt)
    role = result.scalars().first()
    if not role:
        raise ValueError(f"Role '{invite.role_name}' not found.")    # <-- CHANGED

    db_user = User(
        email=invite.email,
        role_id=role.id,
        is_active=False,
        is_password_set=False,
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    # Generate activation token JTI with short expiry (24h)
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    activation_token = jwt.encode(
        {"sub": str(db_user.id), "jti": jti, "exp": expire},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    db_user.activation_token_jti = jti
    await session.commit()
    return activation_token, db_user.email

async def activate_user(session: AsyncSession, token: str, password: str) -> bool:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id or not jti:
            return False

        user = await session.get(User, uuid.UUID(user_id))
        if not user or user.activation_token_jti != jti or user.is_password_set:
            return False

        user.hashed_password = hash_password(password)
        user.is_active = True
        user.is_password_set = True
        user.activation_token_jti = None
        await session.commit()
        return True
    except jwt.PyJWTError:
        return False

async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    return result.scalars().first()

# ==========================================
# PATIENT PROFILE (PHI) DATA ACCESS
# ==========================================
async def create_patient_profile(session: AsyncSession, profile: PatientProfileCreate, user_id: str) -> PatientProfile:
    db_profile = PatientProfile(
        **profile.model_dump(),
        user_id=uuid.UUID(user_id)
    )
    session.add(db_profile)
    await session.commit()
    await session.refresh(db_profile)
    return db_profile

async def get_patient_profile_by_user(session: AsyncSession, user_id: str) -> PatientProfile | None:
    stmt = select(PatientProfile).where(PatientProfile.user_id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    return result.scalars().first()

async def get_patient_profile_by_id(session: AsyncSession, profile_id: str) -> PatientProfile | None:
    return await session.get(PatientProfile, uuid.UUID(profile_id))

async def get_all_patient_profiles(session: AsyncSession, limit: int = 100, offset: int = 0) -> list[PatientProfile]:
    stmt = select(PatientProfile).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def update_patient_profile(
    session: AsyncSession,
    profile_id: str,
    update_data: PatientProfileUpdate,
    actor_id: str,
) -> PatientProfile:
    # Fetch current profile (for audit and existence check)
    stmt = select(PatientProfile).where(PatientProfile.id == uuid.UUID(profile_id))
    result = await session.execute(stmt)
    db_profile = result.scalars().first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    # Audit trail snapshot
    history_record = PatientProfileHistory(
        profile_id=db_profile.id,
        changed_by_user_id=uuid.UUID(actor_id),
        old_first_name=db_profile.first_name,
        old_last_name=db_profile.last_name,
        old_date_of_birth=db_profile.date_of_birth,
        old_medical_history=db_profile.medical_history,
    )
    session.add(history_record)

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return db_profile

    # Use client‑supplied version if given, otherwise fallback to current (backward compat)
    expected_version = update_dict.pop("version", None)
    if expected_version is None:
        expected_version = db_profile.version

    new_version = db_profile.version + 1
    stmt_update = (
        update(PatientProfile)
        .where(
            PatientProfile.id == uuid.UUID(profile_id),
            PatientProfile.version == expected_version,
        )
        .values(**update_dict, version=new_version)
        .returning(PatientProfile)
    )
    result = await session.execute(stmt_update)
    updated_profile = result.scalars().first()

    if not updated_profile:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Profile was modified by another user. Please reload and try again."
        )

    await session.commit()
    return updated_profile