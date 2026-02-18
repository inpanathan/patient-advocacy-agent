"""Tests for safety evaluator."""

from __future__ import annotations

from src.observability.safety_evaluator import SafetyEvaluator


class TestSafetyEvaluator:
    """Test safety compliance checks."""

    def test_clean_output_passes(self):
        """Output without violations passes."""
        evaluator = SafetyEvaluator()
        result = evaluator.check_output(
            "Based on the symptoms, this may be consistent with eczema. "
            "Please seek professional medical evaluation."
        )
        assert result.passed
        assert len(result.violations) == 0

    def test_prescription_language_detected(self):
        """Prescription language triggers violation."""
        evaluator = SafetyEvaluator()
        result = evaluator.check_output("Take this medication twice daily for 7 days.")
        assert not result.passed
        assert any("prescription_language" in v for v in result.violations)

    def test_doctor_claim_detected(self):
        """Doctor claim triggers violation."""
        evaluator = SafetyEvaluator()
        result = evaluator.check_output("As your doctor, I recommend rest.")
        assert not result.passed
        assert any("doctor_claim" in v for v in result.violations)

    def test_disclaimer_present(self):
        """Disclaimer check passes when present."""
        evaluator = SafetyEvaluator()
        result = evaluator.check_disclaimer_present(
            "I am not a doctor. Please seek professional medical care."
        )
        assert result.passed

    def test_disclaimer_missing(self):
        """Missing disclaimer triggers violation."""
        evaluator = SafetyEvaluator()
        result = evaluator.check_disclaimer_present("You have eczema.")
        assert not result.passed
        assert "missing_disclaimer" in result.violations

    def test_multiple_violations_reported(self):
        """Multiple violations in same output all reported."""
        evaluator = SafetyEvaluator()
        result = evaluator.check_output(
            "I am a doctor and I prescribe this medication."
        )
        assert not result.passed
        assert len(result.violations) >= 2

    def test_report_generation(self):
        """Safety report aggregates results correctly."""
        evaluator = SafetyEvaluator()
        evaluator.check_output("Safe output about skin condition")
        evaluator.check_output("Take this medication daily")
        evaluator.check_output("Another safe output")

        report = evaluator.generate_report()
        assert report.total_checked == 3
        assert report.total_passed == 2
        assert report.pass_rate > 0.6
        assert "prescription_language" in report.violations_by_type

    def test_reset(self):
        """Reset clears all results."""
        evaluator = SafetyEvaluator()
        evaluator.check_output("test")
        evaluator.reset()
        report = evaluator.generate_report()
        assert report.total_checked == 0
