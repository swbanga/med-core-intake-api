# app/models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, DateTime, text, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app.crypto import EncryptedString

class Base(DeclarativeBase):
    pass

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    users: Mapped[list["User"]] = relationship(back_populates="role", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped["Role"] = relationship(back_populates="users", lazy="joined")
    
    patient_profile: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class PatientProfile(Base):
    """The strict PHI (Protected Health Information) Vault"""
    __tablename__ = "patient_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # The Anchor: Links directly to the authentication identity
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[datetime.date] = mapped_column(Date, nullable=False) #type: ignore    
    medical_history: Mapped[str] = mapped_column(EncryptedString, nullable=True)

    # Relationship back-population
    user: Mapped["User"] = relationship(back_populates="patient_profile")

class PatientProfileHistory(Base):
    """The Immutable Ledger. Append-only. Never deleted. Never updated."""
    __tablename__ = "patient_profiles_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # The record being modified
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False)
    
    # The entity (Doctor/Admin/Patient) making the change
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    # The historical snapshot (What it was BEFORE the change)
    old_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_date_of_birth: Mapped[datetime.date] = mapped_column(Date, nullable=False) # type: ignore
    
    # Encrypted snapshot
    old_medical_history: Mapped[str] = mapped_column(EncryptedString, nullable=True)

    # The exact moment of modification
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))