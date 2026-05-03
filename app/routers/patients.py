from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db_session
from app.schemas import PatientProfileCreate, PatientProfileRead, UserRead, PatientProfileUpdate
from app.oauth2 import get_current_user, RoleChecker
from app import crud

router = APIRouter(prefix="/v1/patients", tags=["Patient PHI Vault"])

# Only roles explicitly defined here can access these routes
require_patient_clearance = RoleChecker(["Patient"])

@router.post(
    "/profile", 
    response_model=PatientProfileRead, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_patient_clearance)]
)
async def create_profile(
    profile: PatientProfileCreate, 
    session: AsyncSession = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user) # <-- JWT INTERROGATION
):
    """
    Creates a medical profile. 
    The user_id is cryptographically extracted from the JWT, neutralizing IDOR attacks.
    """
    try:
        # Pass the extracted JWT ID directly to the CRUD layer
        return await crud.create_patient_profile(session, profile, str(current_user.id))
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="A medical profile already exists for this identity."
        )

@router.get(
    "/profile/me", 
    response_model=PatientProfileRead,
    dependencies=[Depends(require_patient_clearance)]
)
async def get_my_profile(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user) # <-- JWT INTERROGATION
):
    """Fetches the authenticated user's own medical data."""
    profile = await crud.get_patient_profile_by_user(session, str(current_user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Medical profile not found. Please complete intake.")
    return profile

# Create a new authorization matrix for medical staff
require_medical_clearance = RoleChecker(["Doctor", "System_Admin"])

@router.get(
    "/", # Resolves to /v1/patients/
    response_model=list[PatientProfileRead],
    dependencies=[Depends(require_medical_clearance)]
)
async def get_all_profiles(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Max records per page. Capped at 100."),
    offset: int = Query(0, ge=0, description="Number of records to skip.")
):
    """
    MEDICAL CLEARANCE REQUIRED.
    Fetches a paginated list of all patient medical profiles.
    """
    return await crud.get_all_patient_profiles(session, limit=limit, offset=offset)


@router.put(
    "/{profile_id}", 
    response_model=PatientProfileRead,
    dependencies=[Depends(require_medical_clearance)] # ONLY DOCTORS/ADMINS
)
async def modify_patient_profile(
    profile_id: str,
    update_data: PatientProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user)
):
    """
    MEDICAL CLEARANCE REQUIRED.
    Modifies a patient profile and strictly logs the previous state to the audit ledger.
    """
    return await crud.update_patient_profile(
        session=session, 
        profile_id=profile_id, 
        update_data=update_data, 
        actor_id=str(current_user.id) # Capture exactly who is making the change
    )