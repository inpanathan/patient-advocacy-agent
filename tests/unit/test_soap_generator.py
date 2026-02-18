"""Tests for SOAP note generator."""

from __future__ import annotations

import pytest

from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession


class TestSOAPGenerator:
    """Test SOAP note generation."""

    @pytest.mark.asyncio
    async def test_generate_soap_note(self):
        """SOAP note is generated with all four sections."""
        session = PatientSession()
        session.transcript = ["I have a rash on my arm", "It itches a lot"]

        soap = await generate_soap_note(session)
        assert soap.subjective
        assert soap.objective
        assert soap.assessment
        assert soap.plan
        assert len(soap.icd_codes) > 0
        assert soap.disclaimer  # Always includes disclaimer

    @pytest.mark.asyncio
    async def test_soap_includes_disclaimer(self):
        """SOAP note always includes the medical disclaimer."""
        session = PatientSession()
        session.transcript = ["test symptoms"]

        soap = await generate_soap_note(session)
        assert "not a medical diagnosis" in soap.disclaimer

    @pytest.mark.asyncio
    async def test_soap_with_empty_transcript(self):
        """SOAP handles sessions with no transcript."""
        session = PatientSession()
        soap = await generate_soap_note(session)
        assert soap.subjective  # Should still generate something
