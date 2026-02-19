"""Unit tests for repository layer (no database required).

Tests instantiation and method signatures only. Full integration
tests require a running PostgreSQL instance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from src.db.repositories.assignment import AssignmentRepository
from src.db.repositories.base import BaseRepository
from src.db.repositories.case_repo import CaseRepository
from src.db.repositories.facility_repo import FacilityRepository
from src.db.repositories.patient_repo import PatientRepository
from src.db.repositories.user_repo import UserRepository


class TestBaseRepository:
    """Base repository session injection."""

    def test_session_is_stored(self) -> None:
        mock_session = AsyncMock()
        repo = BaseRepository(mock_session)
        assert repo.session is mock_session


class TestRepositoryInstantiation:
    """Verify all repositories can be instantiated."""

    def test_facility_repo(self) -> None:
        repo = FacilityRepository(AsyncMock())
        assert hasattr(repo, "create_pool")
        assert hasattr(repo, "create_facility")
        assert hasattr(repo, "get_facility")
        assert hasattr(repo, "list_facilities")

    def test_user_repo(self) -> None:
        repo = UserRepository(AsyncMock())
        assert hasattr(repo, "create_user")
        assert hasattr(repo, "get_by_email")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "assign_doctor_to_pool")

    def test_patient_repo(self) -> None:
        repo = PatientRepository(AsyncMock())
        assert hasattr(repo, "create_patient")
        assert hasattr(repo, "get_patient")
        assert hasattr(repo, "list_patients")
        assert hasattr(repo, "generate_patient_number")

    def test_case_repo(self) -> None:
        repo = CaseRepository(AsyncMock())
        assert hasattr(repo, "create_case")
        assert hasattr(repo, "get_case")
        assert hasattr(repo, "update_case")
        assert hasattr(repo, "complete_case")
        assert hasattr(repo, "list_doctor_cases")
        assert hasattr(repo, "add_image")
        assert hasattr(repo, "add_audio")
        assert hasattr(repo, "generate_case_number")

    def test_assignment_repo(self) -> None:
        repo = AssignmentRepository(AsyncMock())
        assert hasattr(repo, "assign_least_loaded_doctor")
