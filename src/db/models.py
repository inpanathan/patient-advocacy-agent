"""SQLAlchemy ORM models for the Patient Advocacy Agent.

Defines 8 tables: facility_pools, facilities, users, doctor_pools,
patients, cases, case_images, case_audio.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# ---- Enums ----


class UserRole(enum.StrEnum):
    """User roles for RBAC."""

    admin = "admin"
    doctor = "doctor"


class CaseStatus(enum.StrEnum):
    """Case lifecycle status."""

    in_progress = "in_progress"
    awaiting_review = "awaiting_review"
    under_review = "under_review"
    completed = "completed"
    escalated = "escalated"


class AudioRole(enum.StrEnum):
    """Who produced the audio segment."""

    patient = "patient"
    system = "system"


class Sex(enum.StrEnum):
    """Biological sex for clinical context."""

    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


# ---- Models ----


class FacilityPool(Base):
    """A geographic or administrative grouping of facilities."""

    __tablename__ = "facility_pools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    facilities: Mapped[list[Facility]] = relationship(back_populates="pool")
    doctor_pools: Mapped[list[DoctorPool]] = relationship(back_populates="pool")


class Facility(Base):
    """A clinic or health post where patients are seen."""

    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facility_pools.id"), nullable=False
    )
    facility_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float | None] = mapped_column(default=None)
    longitude: Mapped[float | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pool: Mapped[FacilityPool] = relationship(back_populates="facilities")
    users: Mapped[list[User]] = relationship(back_populates="facility")
    patients: Mapped[list[Patient]] = relationship(back_populates="facility")
    cases: Mapped[list[Case]] = relationship(back_populates="facility")


class User(Base):
    """An admin or doctor user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False), nullable=False
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    facility: Mapped[Facility | None] = relationship(back_populates="users")
    doctor_pools: Mapped[list[DoctorPool]] = relationship(back_populates="doctor")
    admin_cases: Mapped[list[Case]] = relationship(
        back_populates="admin", foreign_keys="Case.admin_id"
    )
    doctor_cases: Mapped[list[Case]] = relationship(
        back_populates="doctor", foreign_keys="Case.doctor_id"
    )


class DoctorPool(Base):
    """Many-to-many: which doctors serve which facility pools."""

    __tablename__ = "doctor_pools"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facility_pools.id"), primary_key=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    doctor: Mapped[User] = relationship(back_populates="doctor_pools")
    pool: Mapped[FacilityPool] = relationship(back_populates="doctor_pools")


class Patient(Base):
    """A patient record (no PII — uses pseudonymous identifiers)."""

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    patient_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    age_range: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sex: Mapped[Sex] = mapped_column(
        Enum(Sex, name="sex", native_enum=False), default=Sex.unknown, nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    facility: Mapped[Facility] = relationship(back_populates="patients")
    cases: Mapped[list[Case]] = relationship(back_populates="patient")


class Case(Base):
    """A clinical case tying patient, facility, admin, and doctor together."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status", native_enum=False),
        default=CaseStatus.in_progress,
        nullable=False,
    )
    soap_note: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    icd_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    interview_transcript: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    facility: Mapped[Facility] = relationship(back_populates="cases")
    patient: Mapped[Patient] = relationship(back_populates="cases")
    admin: Mapped[User] = relationship(back_populates="admin_cases", foreign_keys=[admin_id])
    doctor: Mapped[User | None] = relationship(
        back_populates="doctor_cases", foreign_keys=[doctor_id]
    )
    images: Mapped[list[CaseImage]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    audio_segments: Mapped[list[CaseAudio]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class CaseImage(Base):
    """An image captured during a case."""

    __tablename__ = "case_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rag_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[Case] = relationship(back_populates="images")


class CaseAudio(Base):
    """An audio segment captured during a case."""

    __tablename__ = "case_audio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[AudioRole] = mapped_column(
        Enum(AudioRole, name="audio_role", native_enum=False), nullable=False
    )
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[Case] = relationship(back_populates="audio_segments")


# Add a unique constraint for doctor_pools
DoctorPool.__table__.append_constraint(
    UniqueConstraint("doctor_id", "pool_id", name="uq_doctor_pool")
)
