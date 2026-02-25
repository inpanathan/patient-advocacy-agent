"""Evaluation for MedGemma QLoRA fine-tuning.

Compares base vs fine-tuned MedGemma on held-out SCIN records.
Metrics: SOAP section completeness, ICD code accuracy, confidence calibration.

Covers: REQ-MOD-002, REQ-TST-004
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

ICD_PATTERN = re.compile(r"[A-Z]\d{2}(?:\.\d{1,2})?")

SOAP_SECTIONS = ("subjective", "objective", "assessment", "plan")


def _extract_sections(text: str) -> dict[str, str]:
    """Parse SOAP sections from model output."""
    sections: dict[str, str] = {}
    current = ""
    lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip().lower()
        for section in (*SOAP_SECTIONS, "icd codes", "confidence"):
            if stripped.startswith(f"## {section}"):
                if current:
                    sections[current] = "\n".join(lines).strip()
                current = section.replace(" ", "_")
                lines = []
                break
        else:
            lines.append(line)

    if current:
        sections[current] = "\n".join(lines).strip()
    return sections


def soap_completeness(output: str) -> float:
    """Fraction of SOAP sections present and non-empty (0.0 to 1.0)."""
    sections = _extract_sections(output)
    present = sum(1 for s in SOAP_SECTIONS if sections.get(s, "").strip())
    return present / len(SOAP_SECTIONS)


def icd_accuracy(output: str, expected_icd: str) -> float:
    """Check if expected ICD code appears in the model output."""
    found_codes = ICD_PATTERN.findall(output)
    if expected_icd in found_codes:
        return 1.0
    # Partial match: check prefix (e.g., L20 matches L20.0)
    prefix = expected_icd.split(".")[0]
    if any(c.startswith(prefix) for c in found_codes):
        return 0.5
    return 0.0


def confidence_calibration(output: str) -> float | None:
    """Extract confidence score from model output."""
    sections = _extract_sections(output)
    conf_text = sections.get("confidence", "")
    match = re.search(r"(\d+(?:\.\d+)?)", conf_text)
    if match:
        val = float(match.group(1))
        return val if val <= 1.0 else val / 100.0
    return None


def evaluate_examples(
    examples: list[dict[str, str]],
    generate_fn: object,
) -> dict[str, float]:
    """Evaluate model on a list of examples.

    Args:
        examples: List of dicts with "input" and "output" keys.
            The "output" field should contain expected ICD codes.
        generate_fn: Callable that takes an input string and returns model output text.

    Returns:
        Dict with aggregate metrics.
    """
    completeness_scores: list[float] = []
    icd_scores: list[float] = []
    confidences: list[float] = []
    latencies: list[float] = []

    for i, ex in enumerate(examples):
        t0 = time.monotonic()
        try:
            output = generate_fn(ex["input"])  # type: ignore[operator]
        except Exception as e:
            logger.warning("eval_generation_failed", index=i, error=str(e))
            continue
        elapsed = time.monotonic() - t0
        latencies.append(elapsed)

        completeness_scores.append(soap_completeness(output))

        # Extract expected ICD from the reference output
        expected_icds = ICD_PATTERN.findall(ex.get("output", ""))
        if expected_icds:
            icd_scores.append(icd_accuracy(output, expected_icds[0]))

        conf = confidence_calibration(output)
        if conf is not None:
            confidences.append(conf)

        logger.info(
            "eval_example",
            index=i,
            completeness=completeness_scores[-1],
            icd_match=icd_scores[-1] if icd_scores else None,
            latency_s=f"{elapsed:.2f}",
        )

    n = len(completeness_scores) or 1
    results = {
        "n_examples": len(completeness_scores),
        "soap_completeness_mean": sum(completeness_scores) / n,
        "icd_accuracy_mean": sum(icd_scores) / len(icd_scores) if icd_scores else 0.0,
        "confidence_mean": sum(confidences) / len(confidences) if confidences else 0.0,
        "latency_mean_s": sum(latencies) / len(latencies) if latencies else 0.0,
        "latency_p95_s": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0,
    }

    logger.info("eval_complete", **results)
    return results


def main() -> None:
    """CLI entry point for fine-tuning evaluation."""
    import argparse

    from src.utils.logger import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="Evaluate MedGemma fine-tuning")
    parser.add_argument(
        "--val-data",
        default="data/processed/finetune/val.jsonl",
        help="Path to validation JSONL",
    )
    parser.add_argument(
        "--output",
        default="data/processed/finetune/eval_results.json",
        help="Path to save evaluation results",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=0,
        help="Max examples to evaluate (0 = all)",
    )
    args = parser.parse_args()

    val_path = Path(args.val_data)
    if not val_path.exists():
        logger.error("val_data_not_found", path=str(val_path))
        return

    from src.pipelines.finetune_medgemma import load_jsonl

    examples = load_jsonl(val_path)
    if args.max_examples > 0:
        examples = examples[: args.max_examples]

    # Load model (uses settings — will load LoRA if configured)
    from src.models.medical_model import get_medical_model

    model = get_medical_model()

    import asyncio

    async def _generate(prompt: str) -> str:
        response = await model.generate(prompt)
        return response.text

    def generate_sync(prompt: str) -> str:
        return asyncio.run(_generate(prompt))

    results = evaluate_examples(examples, generate_sync)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("eval_results_saved", path=str(output_path))


if __name__ == "__main__":
    main()
