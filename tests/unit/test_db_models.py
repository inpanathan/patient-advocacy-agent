"""Tests for ORM model definitions, enums, and relationships."""

from __future__ import annotations

import uuid

from src.db.models import (
    AudioRole,
    Base,
    Case,
    CaseAudio,
    CaseImage,
    CaseStatus,
    DoctorPool,
    Facility,
    FacilityPool,
    Patient,
    Sex,
    User,
    UserRole,
)


class TestEnums:
    """Verify enum values match expected strings."""

    def test_user_role_values(self) -> None:
        assert UserRole.admin.value == "admin"
        assert UserRole.doctor.value == "doctor"

    def test_case_status_values(self) -> None:
        assert CaseStatus.in_progress.value == "in_progress"
        assert CaseStatus.awaiting_review.value == "awaiting_review"
        assert CaseStatus.under_review.value == "under_review"
        assert CaseStatus.completed.value == "completed"
        assert CaseStatus.escalated.value == "escalated"

    def test_audio_role_values(self) -> None:
        assert AudioRole.patient.value == "patient"
        assert AudioRole.system.value == "system"

    def test_sex_values(self) -> None:
        assert Sex.male.value == "male"
        assert Sex.female.value == "female"
        assert Sex.other.value == "other"
        assert Sex.unknown.value == "unknown"


class TestModelInstantiation:
    """Verify models can be instantiated without a database."""

    def test_facility_pool(self) -> None:
        pool = FacilityPool(
            pool_code="POOL-001",
            name="Southern Region",
            region="Tamil Nadu",
        )
        assert pool.pool_code == "POOL-001"
        assert pool.name == "Southern Region"
        assert pool.region == "Tamil Nadu"

    def test_facility(self) -> None:
        pool_id = uuid.uuid4()
        f = Facility(
            pool_id=pool_id,
            facility_code="FAC-001",
            name="Village Clinic A",
            location="Village A, District B",
        )
        assert f.pool_id == pool_id
        assert f.facility_code == "FAC-001"

    def test_user(self) -> None:
        u = User(
            email="doc@test.com",
            password_hash="hashed",
            name="Dr. Test",
            role=UserRole.doctor,
        )
        assert u.email == "doc@test.com"
        assert u.role == UserRole.doctor

    def test_doctor_pool(self) -> None:
        dp = DoctorPool(
            doctor_id=uuid.uuid4(),
            pool_id=uuid.uuid4(),
            is_active=True,
        )
        assert dp.is_active is True

    def test_patient(self) -> None:
        p = Patient(
            facility_id=uuid.uuid4(),
            patient_number="PAT-2024-001",
            age_range="30-40",
            sex=Sex.female,
            language="hi",
        )
        assert p.patient_number == "PAT-2024-001"
        assert p.sex == Sex.female

    def test_case(self) -> None:
        c = Case(
            case_number="CASE-2024-001",
            facility_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            admin_id=uuid.uuid4(),
            status=CaseStatus.in_progress,
        )
        assert c.case_number == "CASE-2024-001"
        assert c.status == CaseStatus.in_progress

    def test_case_image(self) -> None:
        ci = CaseImage(
            case_id=uuid.uuid4(),
            file_path="/data/uploads/img.jpg",
            consent_given=True,
        )
        assert ci.consent_given is True

    def test_case_audio(self) -> None:
        ca = CaseAudio(
            case_id=uuid.uuid4(),
            role=AudioRole.patient,
            transcript="Hello doctor",
            duration_ms=3500,
        )
        assert ca.role == AudioRole.patient
        assert ca.duration_ms == 3500


class TestMetadata:
    """Verify all tables are registered on Base.metadata."""

    def test_all_tables_registered(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "facility_pools",
            "facilities",
            "users",
            "doctor_pools",
            "patients",
            "cases",
            "case_images",
            "case_audio",
        }
        assert expected.issubset(table_names)
