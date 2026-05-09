from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi_limiter.depends import RateLimiter
import uuid

from app.database import get_db_session
from app.schemas import PatientProfileCreate, PatientProfileRead, PatientProfileUpdate
from app.oauth2 import get_current_user, RoleChecker
from app import crud
from app.models import User  # for proper typing

router = APIRouter(prefix="/v1/patients", tags=["Patient PHI Vault"])

require_patient_clearance = RoleChecker(["Patient"])
require_read_all_phi = RoleChecker(["Doctor", "System_Admin", "Auditor"])
require_modify_phi = RoleChecker(["Doctor", "System_Admin"])  # Auditor cannot modify

@router.post(
    "/profile",
    response_model=PatientProfileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_patient_clearance), Depends(RateLimiter(times=5, seconds=60))],
)
async def create_profile(
    profile: PatientProfileCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return await crud.create_patient_profile(session, profile, str(current_user.id))
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A medical profile already exists for this identity.")


@router.get(
    "/profile/me",
    response_model=PatientProfileRead,
    dependencies=[Depends(require_patient_clearance), Depends(RateLimiter(times=10, seconds=60))],
)
async def get_my_profile(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    profile = await crud.get_patient_profile_by_user(session, str(current_user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Medical profile not found. Please complete intake.")
    return profile


@router.get(
    "/",
    response_model=list[PatientProfileRead],
    dependencies=[Depends(require_read_all_phi), Depends(RateLimiter(times=10, seconds=60))],
)
async def get_all_profiles(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await crud.get_all_patient_profiles(session, limit=limit, offset=offset)


@router.put(
    "/{profile_id}",
    response_model=PatientProfileRead,
    dependencies=[Depends(require_modify_phi), Depends(RateLimiter(times=5, seconds=60))],
)
async def modify_patient_profile(
    profile_id: str,
    update_data: PatientProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    return await crud.update_patient_profile(
        session=session,
        profile_id=profile_id,
        update_data=update_data,
        actor_id=str(current_user.id),
    )


@router.get(
    "/profile/{profile_id}",
    response_model=PatientProfileRead,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def get_patient_profile(
    profile_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    ABAC: Owner, Doctor, System_Admin, or Auditor can view.
    """
    profile = await crud.get_patient_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    # Authorization
    is_owner = str(profile.user_id) == str(current_user.id)
    actor_role = current_user.role.name if current_user.role else ""
    if not is_owner and actor_role not in ["Doctor", "System Admin", "Auditor"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return profile