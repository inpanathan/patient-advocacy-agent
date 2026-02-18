"""Tests for case history formatting."""

from __future__ import annotations

from src.models.protocols.medical import SOAPNote
from src.pipelines.case_history import format_case_history
from src.utils.session import PatientSession


class TestCaseHistory:
    """Test case history formatting."""

    def test_format_case_history(self):
        """Case history is properly formatted."""
        session = PatientSession()
        session.detected_language = "hi"
        session.transcript = ["I have a rash"]

        soap = SOAPNote(
            subjective="Patient reports rash",
            objective="Erythematous patches observed",
            assessment="Consistent with eczema (L20.0)",
            plan="Refer to dermatologist",
            icd_codes=["L20.0"],
            confidence=0.8,
        )

        case = format_case_history(session, soap, ["Eczema", "Psoriasis"])
        assert case.case_id.startswith("CASE-")
        assert case.patient_language == "hi"
        assert case.icd_codes == ["L20.0"]
        assert len(case.rag_similar_cases) == 2
        assert case.disclaimer

    def test_escalated_case(self):
        """Escalated sessions are marked in case history."""
        session = PatientSession()
        session.mark_escalated("suspected melanoma")

        soap = SOAPNote(icd_codes=["L43.0"])
        case = format_case_history(session, soap)
        assert case.escalated is True
        assert "melanoma" in case.escalation_reason
