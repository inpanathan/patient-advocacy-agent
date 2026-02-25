"""Tests for MedGemma QLoRA fine-tuning pipeline.

Tests data preparation, instruction formatting, and evaluation metrics.
Does NOT test actual model loading (requires GPU + model weights).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.data.scin_schema import FitzpatrickType, SCINRecord
from src.evaluation.finetune_eval import (
    confidence_calibration,
    icd_accuracy,
    soap_completeness,
)
from src.pipelines.prepare_finetune_data import (
    _build_input,
    _build_output,
    prepare_finetune_records,
    save_jsonl,
)

# ── Fixtures ──────────────────────────────────────────────────────────

_FITZ_CYCLE = [
    FitzpatrickType.I,
    FitzpatrickType.II,
    FitzpatrickType.III,
    FitzpatrickType.IV,
    FitzpatrickType.V,
    FitzpatrickType.VI,
]


@pytest.fixture()
def sample_record() -> SCINRecord:
    """A minimal SCIN record for testing."""
    return SCINRecord(
        record_id="test-001",
        image_path="images/test.jpg",
        diagnosis="Atopic dermatitis",
        icd_code="L20.0",
        fitzpatrick_type=FitzpatrickType.III,
        body_location="left arm",
        severity="moderate",
        description="Red, itchy patches on the left arm",
        age_group="adult",
    )


@pytest.fixture()
def sample_records() -> list[SCINRecord]:
    """A small list of SCIN records for testing."""
    records = []
    for i in range(20):
        records.append(
            SCINRecord(
                record_id=f"test-{i:03d}",
                image_path=f"images/test_{i}.jpg",
                diagnosis="Atopic dermatitis" if i % 2 == 0 else "Contact dermatitis",
                icd_code="L20.0" if i % 2 == 0 else "L25.9",
                fitzpatrick_type=_FITZ_CYCLE[i % 6],
                body_location="arm" if i % 3 == 0 else "trunk",
                severity=["mild", "moderate", "severe"][i % 3],
                description=f"Test description {i}",
            )
        )
    return records


@pytest.fixture()
def sample_soap_output() -> str:
    """A well-formed SOAP note for testing."""
    return (
        "## Subjective\n"
        "Patient reports skin condition on left arm.\n\n"
        "## Objective\n"
        "Fitzpatrick type III. Red patches visible.\n\n"
        "## Assessment\n"
        "Atopic dermatitis (ICD-10: L20.0). Moderate severity.\n\n"
        "## Plan\n"
        "Refer to dermatology. Apply emollient.\n\n"
        "## ICD Codes\nL20.0\n\n"
        "## Confidence\n0.85"
    )


# ── Data Preparation Tests ────────────────────────────────────────────


class TestBuildInput:
    def test_includes_diagnosis(self, sample_record: SCINRecord) -> None:
        result = _build_input(sample_record)
        assert "Atopic dermatitis" in result

    def test_includes_body_location(self, sample_record: SCINRecord) -> None:
        result = _build_input(sample_record)
        assert "left arm" in result

    def test_includes_severity(self, sample_record: SCINRecord) -> None:
        result = _build_input(sample_record)
        assert "moderate" in result

    def test_includes_fitzpatrick(self, sample_record: SCINRecord) -> None:
        result = _build_input(sample_record)
        assert "III" in result

    def test_includes_description(self, sample_record: SCINRecord) -> None:
        result = _build_input(sample_record)
        assert "Red, itchy patches" in result


class TestBuildOutput:
    def test_has_soap_sections(self, sample_record: SCINRecord) -> None:
        result = _build_output(sample_record)
        assert "## Subjective" in result
        assert "## Objective" in result
        assert "## Assessment" in result
        assert "## Plan" in result

    def test_has_icd_code(self, sample_record: SCINRecord) -> None:
        result = _build_output(sample_record)
        assert "L20.0" in result

    def test_has_confidence(self, sample_record: SCINRecord) -> None:
        result = _build_output(sample_record)
        assert "## Confidence" in result


class TestPrepareFinetune:
    def test_split_ratio(self, sample_records: list[SCINRecord]) -> None:
        train, val = prepare_finetune_records(sample_records, val_fraction=0.1, seed=42)
        assert len(train) + len(val) == len(sample_records)
        assert len(val) >= 1  # at least 1 for validation

    def test_deterministic_split(self, sample_records: list[SCINRecord]) -> None:
        train1, val1 = prepare_finetune_records(sample_records, seed=42)
        train2, val2 = prepare_finetune_records(sample_records, seed=42)
        assert train1 == train2
        assert val1 == val2

    def test_different_seed_different_split(self, sample_records: list[SCINRecord]) -> None:
        train1, _ = prepare_finetune_records(sample_records, seed=42)
        train2, _ = prepare_finetune_records(sample_records, seed=99)
        assert train1 != train2

    def test_example_structure(self, sample_records: list[SCINRecord]) -> None:
        train, _ = prepare_finetune_records(sample_records)
        for ex in train:
            assert "input" in ex
            assert "output" in ex
            assert len(ex["input"]) > 0
            assert len(ex["output"]) > 0


class TestSaveJsonl:
    def test_saves_valid_jsonl(self, tmp_path: Path) -> None:
        records = [
            {"input": "test input 1", "output": "test output 1"},
            {"input": "test input 2", "output": "test output 2"},
        ]
        path = tmp_path / "test.jsonl"
        save_jsonl(records, path)

        assert path.exists()
        loaded = []
        with open(path) as f:
            for line in f:
                loaded.append(json.loads(line))
        assert len(loaded) == 2
        assert loaded[0]["input"] == "test input 1"


# ── Evaluation Metric Tests ──────────────────────────────────────────


class TestSoapCompleteness:
    def test_full_soap(self, sample_soap_output: str) -> None:
        assert soap_completeness(sample_soap_output) == 1.0

    def test_missing_section(self) -> None:
        partial = "## Subjective\nSomething\n\n## Objective\nSomething"
        assert soap_completeness(partial) == 0.5

    def test_empty_string(self) -> None:
        assert soap_completeness("") == 0.0

    def test_no_sections(self) -> None:
        assert soap_completeness("Just some random text") == 0.0


class TestIcdAccuracy:
    def test_exact_match(self) -> None:
        output = "ICD codes: L20.0"
        assert icd_accuracy(output, "L20.0") == 1.0

    def test_prefix_match(self) -> None:
        output = "ICD codes: L20.9"
        assert icd_accuracy(output, "L20.0") == 0.5

    def test_no_match(self) -> None:
        output = "ICD codes: L30.9"
        assert icd_accuracy(output, "L20.0") == 0.0

    def test_no_codes_in_output(self) -> None:
        output = "No ICD codes found"
        assert icd_accuracy(output, "L20.0") == 0.0


class TestConfidenceCalibration:
    def test_extracts_confidence(self, sample_soap_output: str) -> None:
        result = confidence_calibration(sample_soap_output)
        assert result == 0.85

    def test_no_confidence(self) -> None:
        assert confidence_calibration("## Subjective\nSomething") is None

    def test_percentage_normalization(self) -> None:
        output = "## Confidence\n85"
        result = confidence_calibration(output)
        assert result == 0.85


# ── LoRA Loader Tests ────────────────────────────────────────────────


class TestLoraLoader:
    def test_skips_when_no_path_configured(self) -> None:
        from src.pipelines.lora_loader import maybe_apply_lora_adapter

        with patch("src.pipelines.lora_loader.settings") as mock_settings:
            mock_settings.llm.lora_adapter_path = ""
            # Should not raise
            maybe_apply_lora_adapter(object())

    def test_warns_when_path_not_found(self) -> None:
        from src.pipelines.lora_loader import maybe_apply_lora_adapter

        with patch("src.pipelines.lora_loader.settings") as mock_settings:
            mock_settings.llm.lora_adapter_path = "/nonexistent/path"
            # Should not raise, just warn
            maybe_apply_lora_adapter(object())

    def test_warns_when_model_has_no_attribute(self, tmp_path: Path) -> None:
        from src.pipelines.lora_loader import maybe_apply_lora_adapter

        with patch("src.pipelines.lora_loader.settings") as mock_settings:
            mock_settings.llm.lora_adapter_path = str(tmp_path)
            # Object without _model attribute — should warn, not crash
            maybe_apply_lora_adapter(object())
