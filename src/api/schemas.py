"""Pydantic request/response schemas for the multi-tenant clinical workflow."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ---- Facility ----


class CreateFacilityPoolRequest(BaseModel):
    pool_code: str
    name: str
    region: str


class FacilityPoolResponse(BaseModel):
    id: str
    pool_code: str
    name: str
    region: str


class CreateFacilityRequest(BaseModel):
    pool_id: str
    facility_code: str
    name: str
    location: str
    latitude: float | None = None
    longitude: float | None = None


class FacilityResponse(BaseModel):
    id: str
    pool_id: str
    facility_code: str
    name: str
    location: str
    latitude: float | None
    longitude: float | None


# ---- Patient ----


class CreatePatientRequest(BaseModel):
    facility_id: str
    age_range: str | None = None
    sex: str = "unknown"
    language: str = "en"


class PatientResponse(BaseModel):
    id: str
    facility_id: str
    patient_number: str
    age_range: str | None
    sex: str
    language: str
    created_at: datetime


# ---- Case ----


class StartCaseRequest(BaseModel):
    facility_id: str
    patient_id: str


class CaseResponse(BaseModel):
    id: str
    case_number: str
    facility_id: str
    patient_id: str
    admin_id: str
    doctor_id: str | None
    status: str
    escalated: bool
    image_count: int = 0
    created_at: datetime
    updated_at: datetime


class CaseSummaryResponse(BaseModel):
    id: str
    case_number: str
    status: str
    soap_note: dict | None
    icd_codes: list[str] | None
    interview_transcript: list[dict] | None
    doctor_notes: str | None
    escalated: bool
    images: list[CaseImageResponse]


class CaseImageResponse(BaseModel):
    id: str
    file_path: str
    consent_given: bool
    rag_results: dict | None
    created_at: datetime


class CaseAudioResponse(BaseModel):
    id: str
    role: str
    transcript: str | None
    duration_ms: int | None
    created_at: datetime


# ---- Doctor ----


class DoctorCaseResponse(BaseModel):
    id: str
    case_number: str
    patient_id: str
    facility_id: str
    status: str
    escalated: bool
    soap_note: dict | None
    icd_codes: list[str] | None
    doctor_notes: str | None
    image_count: int = 0
    created_at: datetime


class DoctorNotesRequest(BaseModel):
    notes: str


class DoctorCompleteRequest(BaseModel):
    notes: str | None = None
    final_icd_codes: list[str] | None = None


# Resolve forward reference
CaseSummaryResponse.model_rebuild()
