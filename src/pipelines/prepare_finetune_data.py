"""Prepare SCIN records for MedGemma QLoRA fine-tuning.

Converts SCIN dermatology records into instruction-tuning format
(input prompt + expected SOAP note output) and splits into train/val.

Covers: REQ-MOD-001
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import structlog

from src.data.scin_schema import SCINRecord

logger = structlog.get_logger(__name__)

# Severity-based plan templates
_PLAN_TEMPLATES: dict[str, str] = {
    "mild": (
        "- Monitor for changes over the next 2-4 weeks\n"
        "- Apply emollient or barrier cream as appropriate\n"
        "- Return if symptoms worsen or do not improve\n"
        "- Seek professional medical help for definitive diagnosis"
    ),
    "moderate": (
        "- Refer to dermatology for further evaluation within 1-2 weeks\n"
        "- Consider topical therapy pending specialist review\n"
        "- Photograph progression for comparison at follow-up\n"
        "- Seek professional medical help — this requires physician review"
    ),
    "severe": (
        "- URGENT: Refer to dermatology within 48 hours\n"
        "- Consider biopsy if malignancy is suspected\n"
        "- Document extent and distribution for specialist\n"
        "- Seek professional medical help immediately"
    ),
    "unknown": (
        "- Refer to dermatology for assessment\n"
        "- Document current presentation with photographs\n"
        "- Seek professional medical help for proper evaluation"
    ),
}


def _build_input(record: SCINRecord) -> str:
    """Build the instruction prompt from a SCIN record."""
    location = record.body_location or "unspecified location"
    parts = [
        f"Patient presents with {record.diagnosis} on {location}.",
        f"Severity: {record.severity}.",
        f"Fitzpatrick type: {record.fitzpatrick_type}.",
    ]
    if record.description:
        parts.append(f"Description: {record.description}")
    if record.age_group:
        parts.append(f"Age group: {record.age_group}.")
    return " ".join(parts)


def _build_output(record: SCINRecord) -> str:
    """Build the expected SOAP note output from a SCIN record."""
    subjective = (
        f"Patient reports skin condition identified as {record.diagnosis}. "
        f"Located on {record.body_location or 'unspecified area'}. "
        f"Severity described as {record.severity}."
    )
    if record.description:
        subjective += f" {record.description}"

    objective = (
        f"Fitzpatrick skin type {record.fitzpatrick_type}. "
        f"Visual assessment consistent with {record.diagnosis}. "
        f"Body location: {record.body_location or 'not specified'}."
    )

    assessment = (
        f"Primary assessment: {record.diagnosis} (ICD-10: {record.icd_code}). "
        f"Severity: {record.severity}. "
        f"Differential diagnoses should be considered by the reviewing physician."
    )

    plan = _PLAN_TEMPLATES.get(record.severity, _PLAN_TEMPLATES["unknown"])

    return (
        f"## Subjective\n{subjective}\n\n"
        f"## Objective\n{objective}\n\n"
        f"## Assessment\n{assessment}\n\n"
        f"## Plan\n{plan}\n\n"
        f"## ICD Codes\n{record.icd_code}\n\n"
        f"## Confidence\n0.85"
    )


def prepare_finetune_records(
    records: list[SCINRecord],
    val_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Convert SCIN records to instruction-tuning pairs and split train/val.

    Args:
        records: Validated SCIN records.
        val_fraction: Fraction of records for validation (default 10%).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (train_examples, val_examples). Each example has
        "input" and "output" keys.
    """
    rng = random.Random(seed)

    examples = []
    for record in records:
        examples.append(
            {
                "input": _build_input(record),
                "output": _build_output(record),
            }
        )

    rng.shuffle(examples)
    split_idx = max(1, int(len(examples) * val_fraction))
    val = examples[:split_idx]
    train = examples[split_idx:]

    logger.info(
        "finetune_data_prepared",
        total=len(examples),
        train=len(train),
        val=len(val),
        val_fraction=val_fraction,
    )
    return train, val


def save_jsonl(records: list[dict[str, str]], path: Path) -> None:
    """Write records as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("jsonl_saved", path=str(path), count=len(records))


def main() -> None:
    """CLI entry point: load SCIN metadata, prepare fine-tuning data."""
    import argparse

    from src.utils.config import settings
    from src.utils.logger import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="Prepare SCIN data for MedGemma fine-tuning")
    parser.add_argument(
        "--data-dir",
        default=settings.scin.data_dir,
        help="Path to SCIN data directory",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed/finetune",
        help="Output directory for JSONL files",
    )
    parser.add_argument(
        "--val-fraction",
        type=float,
        default=0.1,
        help="Fraction of data for validation",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    metadata_path = data_dir / "metadata.json"

    if not metadata_path.exists():
        logger.error("metadata_not_found", path=str(metadata_path))
        return

    with open(metadata_path) as f:
        raw = json.load(f)

    raw_records = raw if isinstance(raw, list) else raw.get("records", [])

    records = []
    for r in raw_records:
        try:
            records.append(SCINRecord(**r))
        except (TypeError, ValueError) as e:
            logger.warning("skipping_invalid_record", error=str(e))

    if not records:
        logger.warning("no_valid_records")
        return

    train, val = prepare_finetune_records(records, val_fraction=args.val_fraction, seed=args.seed)

    output_dir = Path(args.output_dir)
    save_jsonl(train, output_dir / "train.jsonl")
    save_jsonl(val, output_dir / "val.jsonl")

    logger.info(
        "finetune_data_preparation_complete",
        train_path=str(output_dir / "train.jsonl"),
        val_path=str(output_dir / "val.jsonl"),
    )


if __name__ == "__main__":
    main()
