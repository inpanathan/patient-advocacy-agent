"""Seed the database with sample data for development.

Creates: 1 pool, 2 facilities, 2 admins, 3 doctors, and sample patients.

Usage:
    uv run python scripts/seed_db.py
"""

from __future__ import annotations

import asyncio

from src.auth.password import hash_password
from src.db.engine import get_session_factory, init_db
from src.db.models import UserRole
from src.db.repositories.facility_repo import FacilityRepository
from src.db.repositories.patient_repo import PatientRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

DEFAULT_PASSWORD = "test"


async def seed() -> None:
    """Seed the database with development data."""
    await init_db()
    factory = get_session_factory()

    async with factory() as session:
        repo_facility = FacilityRepository(session)
        repo_user = UserRepository(session)
        repo_patient = PatientRepository(session)

        # ---- Pool ----
        pool = await repo_facility.create_pool(
            pool_code="SOUTH-ASIA-01",
            name="South Asia Region 1",
            region="South Asia",
        )
        logger.info("seeded_pool", pool_id=str(pool.id))

        # ---- Facilities ----
        facility_a = await repo_facility.create_facility(
            pool_id=pool.id,
            facility_code="FAC-TN-001",
            name="Tamil Nadu Village Clinic",
            location="Madurai, Tamil Nadu, India",
            latitude=9.9252,
            longitude=78.1198,
        )
        facility_b = await repo_facility.create_facility(
            pool_id=pool.id,
            facility_code="FAC-KA-001",
            name="Karnataka Health Post",
            location="Mysuru, Karnataka, India",
            latitude=12.2958,
            longitude=76.6394,
        )
        logger.info(
            "seeded_facilities",
            facility_a=str(facility_a.id),
            facility_b=str(facility_b.id),
        )

        # ---- Admins ----
        pw_hash = hash_password(DEFAULT_PASSWORD)

        admin_a = await repo_user.create_user(
            email="admin@test.com",
            password_hash=pw_hash,
            name="Admin Alice",
            role=UserRole.admin,
            facility_id=facility_a.id,
        )
        admin_b = await repo_user.create_user(
            email="admin2@test.com",
            password_hash=pw_hash,
            name="Admin Bob",
            role=UserRole.admin,
            facility_id=facility_b.id,
        )
        logger.info(
            "seeded_admins",
            admin_a=str(admin_a.id),
            admin_b=str(admin_b.id),
        )

        # ---- Doctors ----
        doc1 = await repo_user.create_user(
            email="doctor1@test.com",
            password_hash=pw_hash,
            name="Dr. Priya Sharma",
            role=UserRole.doctor,
        )
        doc2 = await repo_user.create_user(
            email="doctor2@test.com",
            password_hash=pw_hash,
            name="Dr. Raj Patel",
            role=UserRole.doctor,
        )
        doc3 = await repo_user.create_user(
            email="doctor3@test.com",
            password_hash=pw_hash,
            name="Dr. Amara Okafor",
            role=UserRole.doctor,
        )

        # Assign doctors to pool
        await repo_user.assign_doctor_to_pool(doc1.id, pool.id)
        await repo_user.assign_doctor_to_pool(doc2.id, pool.id)
        await repo_user.assign_doctor_to_pool(doc3.id, pool.id)
        logger.info(
            "seeded_doctors",
            doctor_ids=[str(doc1.id), str(doc2.id), str(doc3.id)],
        )

        # ---- Sample Patients ----
        from src.db.models import Sex

        for i, (age, sex, lang) in enumerate(
            [
                ("20-30", Sex.female, "ta"),
                ("40-50", Sex.male, "hi"),
                ("10-20", Sex.female, "bn"),
                ("50-60", Sex.male, "ta"),
                ("30-40", Sex.female, "sw"),
            ],
            start=1,
        ):
            fac = facility_a if i <= 3 else facility_b
            number = await repo_patient.generate_patient_number(fac.id)
            await repo_patient.create_patient(
                facility_id=fac.id,
                patient_number=number,
                age_range=age,
                sex=sex,
                language=lang,
            )

        logger.info("seeded_patients", count=5)

        await session.commit()

    logger.info("seed_complete")


if __name__ == "__main__":
    setup_logging(level="INFO", fmt="console")
    asyncio.run(seed())
