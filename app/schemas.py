import uuid
from datetime import datetime
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
    password: str = Field(..., min_length=12, description="Minimum 12 chars. NIST standard.")
    role_id: uuid.UUID

class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    role: RoleRead | None = None # Nested representation of the role
    
    # CRITICAL: hashed_password is strictly absent from this output model
    model_config = ConfigDict(from_attributes=True)