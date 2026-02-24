"""Unit tests for doctor case review — SOAP confidence, schema validation, RAG results.

Verifies that:
- The soap_dict built from a SOAPNote always carries a confidence key.
- The confidence value is a float in [0, 1].
- CaseSummaryResponse and DoctorCaseResponse both accept a soap_note dict that
  includes the confidence field.
- CaseImageResponse accepts rag_results with the canonical structure produced by
  the image upload endpoint.
- RAG results are preserved end-to-end inside CaseSummaryResponse.images.
- The SOAP generator returns a SOAPNote whose confidence field is a float >= 0.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.api.schemas import CaseImageResponse, CaseSummaryResponse, DoctorCaseResponse
from src.models.protocols.medical import SOAPNote
from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXED_UUID = "11111111-1111-1111-1111-111111111111"
_FIXED_CASE_NUMBER = "CASE-0001"
_NOW = datetime(2026, 2, 24, 12, 0, 0, tzinfo=UTC)


def _make_soap_note(confidence: float = 0.78) -> SOAPNote:
    """Return a fully-populated SOAPNote with the given confidence."""
    return SOAPNote(
        subjective="Patient reports itching and redness on the forearm.",
        objective="Erythematous patch with mild scaling observed.",
        assessment="Consistent with atopic dermatitis (L20.0).",
        plan="Refer to clinic. Moisturiser for symptomatic relief.",
        icd_codes=["L20.0"],
        confidence=confidence,
        disclaimer=(
            "This is an AI-assisted triage assessment, not a medical diagnosis. "
            "Please seek professional medical help for proper evaluation and treatment."
        ),
    )


def _build_soap_dict(soap: SOAPNote) -> dict:
    """Replicate the soap_dict construction used in case_routes.py."""
    return {
        "subjective": soap.subjective,
        "objective": soap.objective,
        "assessment": soap.assessment,
        "plan": soap.plan,
        "confidence": soap.confidence,
        "disclaimer": soap.disclaimer,
    }


def _minimal_case_image_response(
    rag_results: dict | None = None,
) -> CaseImageResponse:
    """Return a CaseImageResponse with the given rag_results payload."""
    return CaseImageResponse(
        id=_FIXED_UUID,
        file_path="data/uploads/case-1/img-1.jpg",
        consent_given=True,
        rag_results=rag_results,
        created_at=_NOW,
    )


# ---------------------------------------------------------------------------
# 1. SOAP dict includes confidence score
# ---------------------------------------------------------------------------


def test_soap_dict_includes_confidence_key() -> None:
    """Building the soap_dict from a SOAPNote always produces a 'confidence' key."""
    soap = _make_soap_note(confidence=0.78)
    soap_dict = _build_soap_dict(soap)

    assert "confidence" in soap_dict


# ---------------------------------------------------------------------------
# 2. SOAP dict confidence is a float between 0 and 1
# ---------------------------------------------------------------------------


def test_soap_dict_confidence_is_float_in_unit_interval() -> None:
    """The confidence value serialised into soap_dict is a float in [0.0, 1.0]."""
    soap = _make_soap_note(confidence=0.78)
    soap_dict = _build_soap_dict(soap)

    assert isinstance(soap_dict["confidence"], float)
    assert 0.0 <= soap_dict["confidence"] <= 1.0


def test_soap_dict_confidence_boundary_zero() -> None:
    """A SOAPNote with confidence=0.0 yields a dict with confidence 0.0."""
    soap = _make_soap_note(confidence=0.0)
    soap_dict = _build_soap_dict(soap)

    assert soap_dict["confidence"] == 0.0


def test_soap_dict_confidence_boundary_one() -> None:
    """A SOAPNote with confidence=1.0 yields a dict with confidence 1.0."""
    soap = _make_soap_note(confidence=1.0)
    soap_dict = _build_soap_dict(soap)

    assert soap_dict["confidence"] == 1.0


# ---------------------------------------------------------------------------
# 3. CaseSummaryResponse schema accepts confidence in soap_note dict
# ---------------------------------------------------------------------------


def test_case_summary_response_accepts_soap_note_with_confidence() -> None:
    """CaseSummaryResponse is constructable when soap_note contains a confidence key."""
    soap = _make_soap_note(confidence=0.82)
    soap_dict = _build_soap_dict(soap)

    summary = CaseSummaryResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        status="completed",
        soap_note=soap_dict,
        icd_codes=["L20.0"],
        interview_transcript=None,
        doctor_notes=None,
        escalated=False,
        images=[],
    )

    assert summary.soap_note is not None
    assert summary.soap_note["confidence"] == 0.82


def test_case_summary_response_soap_note_confidence_value_preserved() -> None:
    """The exact confidence value is preserved after round-tripping through the schema."""
    confidence = 0.654
    soap_dict = _build_soap_dict(_make_soap_note(confidence=confidence))

    summary = CaseSummaryResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        status="completed",
        soap_note=soap_dict,
        icd_codes=[],
        interview_transcript=None,
        doctor_notes=None,
        escalated=False,
        images=[],
    )

    assert summary.soap_note is not None
    assert summary.soap_note["confidence"] == confidence


def test_case_summary_response_accepts_none_soap_note() -> None:
    """CaseSummaryResponse accepts soap_note=None for cases not yet completed."""
    summary = CaseSummaryResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        status="open",
        soap_note=None,
        icd_codes=None,
        interview_transcript=None,
        doctor_notes=None,
        escalated=False,
        images=[],
    )

    assert summary.soap_note is None


# ---------------------------------------------------------------------------
# 4. DoctorCaseResponse schema accepts confidence in soap_note dict
# ---------------------------------------------------------------------------


def test_doctor_case_response_accepts_soap_note_with_confidence() -> None:
    """DoctorCaseResponse is constructable when soap_note dict has a confidence key."""
    soap_dict = _build_soap_dict(_make_soap_note(confidence=0.91))

    response = DoctorCaseResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        patient_id=_FIXED_UUID,
        facility_id=_FIXED_UUID,
        status="under_review",
        escalated=False,
        soap_note=soap_dict,
        icd_codes=["L20.0"],
        doctor_notes=None,
        image_count=1,
        created_at=_NOW,
    )

    assert response.soap_note is not None
    assert isinstance(response.soap_note, dict)
    assert response.soap_note["confidence"] == 0.91


def test_doctor_case_response_accepts_none_soap_note() -> None:
    """DoctorCaseResponse accepts soap_note=None before SOAP has been generated."""
    response = DoctorCaseResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        patient_id=_FIXED_UUID,
        facility_id=_FIXED_UUID,
        status="open",
        escalated=False,
        soap_note=None,
        icd_codes=None,
        doctor_notes=None,
        image_count=0,
        created_at=_NOW,
    )

    assert response.soap_note is None


def test_doctor_case_response_confidence_matches_source_soap_note() -> None:
    """The confidence stored on DoctorCaseResponse matches what was on the SOAPNote."""
    soap = _make_soap_note(confidence=0.55)
    soap_dict = _build_soap_dict(soap)

    response = DoctorCaseResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        patient_id=_FIXED_UUID,
        facility_id=_FIXED_UUID,
        status="completed",
        escalated=False,
        soap_note=soap_dict,
        icd_codes=soap.icd_codes,
        doctor_notes=None,
        image_count=0,
        created_at=_NOW,
    )

    assert response.soap_note is not None
    assert response.soap_note["confidence"] == soap.confidence


# ---------------------------------------------------------------------------
# 5. RAG results structure is correct — CaseImageResponse accepts rag_results
# ---------------------------------------------------------------------------


def test_case_image_response_accepts_rag_results_with_results_key() -> None:
    """CaseImageResponse accepts the canonical rag_results dict produced by upload_image."""
    rag_results = {
        "results": [
            {"diagnosis": "Atopic dermatitis", "icd_code": "L20.0", "score": 0.9231},
            {"diagnosis": "Contact dermatitis", "icd_code": "L25.0", "score": 0.8104},
        ]
    }

    image_resp = _minimal_case_image_response(rag_results=rag_results)

    assert image_resp.rag_results is not None
    assert "results" in image_resp.rag_results


def test_case_image_response_rag_results_list_length_preserved() -> None:
    """The number of RAG result entries is preserved in CaseImageResponse."""
    rag_results = {
        "results": [
            {"diagnosis": "Atopic dermatitis", "icd_code": "L20.0", "score": 0.92},
            {"diagnosis": "Contact dermatitis", "icd_code": "L25.0", "score": 0.81},
            {"diagnosis": "Psoriasis", "icd_code": "L40.0", "score": 0.74},
        ]
    }

    image_resp = _minimal_case_image_response(rag_results=rag_results)

    assert image_resp.rag_results is not None
    assert len(image_resp.rag_results["results"]) == 3


def test_case_image_response_rag_result_entry_has_required_fields() -> None:
    """Each entry in rag_results['results'] exposes diagnosis, icd_code, and score."""
    rag_results = {
        "results": [
            {"diagnosis": "Atopic dermatitis", "icd_code": "L20.0", "score": 0.9231},
        ]
    }

    image_resp = _minimal_case_image_response(rag_results=rag_results)
    assert image_resp.rag_results is not None
    entry = image_resp.rag_results["results"][0]

    assert "diagnosis" in entry
    assert "icd_code" in entry
    assert "score" in entry


def test_case_image_response_accepts_none_rag_results() -> None:
    """CaseImageResponse accepts rag_results=None when RAG retrieval was skipped."""
    image_resp = _minimal_case_image_response(rag_results=None)

    assert image_resp.rag_results is None


def test_case_image_response_rag_results_top_score_is_float() -> None:
    """The score on the top RAG result is a float."""
    rag_results = {
        "results": [
            {"diagnosis": "Atopic dermatitis", "icd_code": "L20.0", "score": 0.9231},
        ]
    }

    image_resp = _minimal_case_image_response(rag_results=rag_results)
    assert image_resp.rag_results is not None
    top_score = image_resp.rag_results["results"][0]["score"]

    assert isinstance(top_score, float)


# ---------------------------------------------------------------------------
# 6. RAG results are preserved in CaseSummaryResponse.images
# ---------------------------------------------------------------------------


def test_case_summary_response_images_preserve_rag_results() -> None:
    """RAG results stored on a CaseImageResponse are accessible via CaseSummaryResponse."""
    rag_results = {
        "results": [
            {"diagnosis": "Eczema", "icd_code": "L20.9", "score": 0.8850},
        ]
    }
    image_resp = _minimal_case_image_response(rag_results=rag_results)

    summary = CaseSummaryResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        status="completed",
        soap_note=_build_soap_dict(_make_soap_note()),
        icd_codes=["L20.9"],
        interview_transcript=None,
        doctor_notes=None,
        escalated=False,
        images=[image_resp],
    )

    assert len(summary.images) == 1
    assert summary.images[0].rag_results is not None
    assert summary.images[0].rag_results["results"][0]["diagnosis"] == "Eczema"


def test_case_summary_response_multiple_images_each_carry_rag_results() -> None:
    """All images in CaseSummaryResponse retain their individual rag_results."""
    rag_a = {"results": [{"diagnosis": "Eczema", "icd_code": "L20.9", "score": 0.88}]}
    rag_b = {"results": [{"diagnosis": "Psoriasis", "icd_code": "L40.0", "score": 0.76}]}

    images = [
        _minimal_case_image_response(rag_results=rag_a),
        _minimal_case_image_response(rag_results=rag_b),
    ]

    summary = CaseSummaryResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        status="completed",
        soap_note=_build_soap_dict(_make_soap_note()),
        icd_codes=["L20.9", "L40.0"],
        interview_transcript=None,
        doctor_notes=None,
        escalated=False,
        images=images,
    )

    assert summary.images[0].rag_results is not None
    assert summary.images[1].rag_results is not None
    assert summary.images[0].rag_results["results"][0]["diagnosis"] == "Eczema"
    assert summary.images[1].rag_results["results"][0]["diagnosis"] == "Psoriasis"


def test_case_summary_response_empty_images_list_is_valid() -> None:
    """CaseSummaryResponse is valid when there are no images."""
    summary = CaseSummaryResponse(
        id=_FIXED_UUID,
        case_number=_FIXED_CASE_NUMBER,
        status="open",
        soap_note=None,
        icd_codes=None,
        interview_transcript=None,
        doctor_notes=None,
        escalated=False,
        images=[],
    )

    assert summary.images == []


# ---------------------------------------------------------------------------
# 7. SOAP generator returns a SOAPNote with a valid confidence field
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_soap_note_confidence_is_float() -> None:
    """generate_soap_note returns a SOAPNote whose confidence field is a float."""
    session = PatientSession()
    session.transcript = ["I have a rash on my arm that itches."]

    soap = await generate_soap_note(session)

    assert isinstance(soap.confidence, float)


@pytest.mark.asyncio
async def test_generate_soap_note_confidence_is_non_negative() -> None:
    """generate_soap_note confidence is >= 0.0."""
    session = PatientSession()
    session.transcript = ["Redness and scaling on left hand."]

    soap = await generate_soap_note(session)

    assert soap.confidence >= 0.0


@pytest.mark.asyncio
async def test_generate_soap_note_confidence_is_at_most_one() -> None:
    """generate_soap_note confidence is <= 1.0 (mock model returns 0.78)."""
    session = PatientSession()
    session.transcript = ["Dry skin with itching for two weeks."]

    soap = await generate_soap_note(session)

    assert soap.confidence <= 1.0


@pytest.mark.asyncio
async def test_generate_soap_note_with_empty_session_confidence_is_float() -> None:
    """generate_soap_note with no transcript still returns a float confidence."""
    session = PatientSession()

    soap = await generate_soap_note(session)

    assert isinstance(soap.confidence, float)


@pytest.mark.asyncio
async def test_generate_soap_note_confidence_present_in_serialised_dict() -> None:
    """The confidence from generate_soap_note survives serialisation into soap_dict."""
    session = PatientSession()
    session.transcript = ["I have a rash."]

    soap = await generate_soap_note(session)
    soap_dict = _build_soap_dict(soap)

    assert "confidence" in soap_dict
    assert isinstance(soap_dict["confidence"], float)
