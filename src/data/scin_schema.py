"""SCIN database schema definitions and validation.

The SCIN (Skin Condition Image Network) database from Harvard contains
dermatological images with metadata. This module defines the expected
schema and provides validation functions.

Covers: REQ-TST-004, REQ-TST-005, REQ-OBS-012
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class FitzpatrickType(StrEnum):
    """Fitzpatrick skin type classification (I-VI)."""

    I = "I"  # noqa: E741
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"
    VI = "VI"


class SCINRecord(BaseModel):
    """Schema for a single SCIN database record.

    Each record represents one dermatological case with image reference,
    diagnosis, ICD codes, and patient metadata.
    """

    record_id: str = Field(..., min_length=1, description="Unique record identifier")
    image_path: str = Field(..., min_length=1, description="Relative path to image file")
    diagnosis: str = Field(..., min_length=1, description="Primary diagnosis label")
    icd_code: str = Field(
        ...,
        pattern=r"^[A-Z]\d{2}(\.\d{1,4})?$",
        description="ICD-10 code (e.g., L20.0)",
    )
    fitzpatrick_type: FitzpatrickType = Field(
        ..., description="Fitzpatrick skin type (I-VI)"
    )
    body_location: str = Field(default="", description="Body location of the condition")
    age_group: str = Field(default="", description="Patient age group (e.g., adult, pediatric)")
    severity: str = Field(default="mild", description="Condition severity: mild, moderate, severe")
    description: str = Field(default="", description="Text description of the condition")
    tags: list[str] = Field(default_factory=list, description="Additional metadata tags")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"mild", "moderate", "severe", "unknown"}
        if v.lower() not in allowed:
            msg = f"severity must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v.lower()

    @field_validator("icd_code")
    @classmethod
    def validate_icd_range(cls, v: str) -> str:
        """Validate ICD code is in dermatology range (L00-L99)."""
        if not v.startswith("L"):
            msg = f"Expected dermatology ICD code (L00-L99), got '{v}'"
            raise ValueError(msg)
        return v


class SCINDatasetStats(BaseModel):
    """Baseline statistics for drift comparison."""

    total_records: int = 0
    records_per_diagnosis: dict[str, int] = Field(default_factory=dict)
    records_per_fitzpatrick: dict[str, int] = Field(default_factory=dict)
    records_per_severity: dict[str, int] = Field(default_factory=dict)
    icd_code_distribution: dict[str, int] = Field(default_factory=dict)
    image_count: int = 0
    missing_fields: dict[str, int] = Field(default_factory=dict)
