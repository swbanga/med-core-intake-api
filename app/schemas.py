import uuid
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, ConfigDict, Field

# ==========================================
# ROLE SCHEMAS (DTOs)
# ==========================================
class RoleBase(BaseModel):
    name: str = Field(..., max_length=50, description="The strict RBAC identifier")
    description: str | None = Field(default=None, max_length=255)

class RoleCreate(RoleBase):
    pass # Used strictly for creating roles

class RoleRead(RoleBase):
    id: uuid.UUID
    
    # Allows Pydantic to parse SQLAlchemy objects seamlessly
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# USER SCHEMAS (DTOs)
# ==========================================
class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Valid email identity vector")
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(
        ..., 
        min_length=12, 
        max_length=64, # <-- THE FIX: Bounces oversized passwords at the door
        description="Min 12 chars. Max 64 chars due to bcrypt 72-byte block limit."
    )
    role_id: uuid.UUID

class UserInvite(BaseModel):
    email: EmailStr
    role_name: str = Field(..., max_length=50)

class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    role: RoleRead | None = None # Nested representation of the role
    
    # CRITICAL: hashed_password is strictly absent from this output model
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# PATIENT PROFILE SCHEMAS (DTOs)
# ==========================================
class PatientProfileBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: date = Field(..., description="ISO 8601 Format: YYYY-MM-DD")
    medical_history: str | None = Field(default=None, description="Pre-existing conditions, allergies, etc.")

class PatientProfileCreate(PatientProfileBase):
    pass # Patients will submit this form after registering an account

class PatientProfileRead(PatientProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    version: int   # for concurrency tracking
    model_config = ConfigDict(from_attributes=True)

class PatientProfileUpdate(BaseModel):
    """Allows partial updates to the medical record."""
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    medical_history: str | None = None