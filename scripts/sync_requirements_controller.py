#!/usr/bin/env python3
"""Sync common_requirements_controller.json from common_requirements.md.

Parses the markdown to extract all REQ-XXX-NNN IDs with their section,
subsection, and summary text, then updates the controller JSON.

- New requirements get implement="N", enable="N"
- Existing requirements preserve their implement/enable values
- Removed requirements are deleted from the JSON
- Section/subsection/summary metadata is always refreshed from markdown

Usage:
    python scripts/sync_requirements_controller.py
    python scripts/sync_requirements_controller.py --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
MD_PATH = DOCS_DIR / "common_requirements.md"
JSON_PATH = DOCS_DIR / "common_requirements_controller.json"

REQ_PATTERN = re.compile(r"- \[ \] \*\*(?P<id>REQ-[A-Z]+-\d+)\*\*:\s*(?P<summary>.+)")
SECTION_PATTERN = re.compile(r"^## \d+\.\s+(?P<name>.+)")
SUBSECTION_PATTERN = re.compile(r"^### \d+\.\d+\s+(?P<name>.+)")


def parse_markdown(path: Path) -> dict[str, dict]:
    """Extract requirements from the markdown file."""
    requirements: dict[str, dict] = {}
    current_section = ""
    current_subsection = ""

    for line in path.read_text().splitlines():
        section_match = SECTION_PATTERN.match(line)
        if section_match:
            # Rebuild the numbered section label (e.g., "1. Agent Interaction")
            num = line.split(".")[0].replace("#", "").strip()
            current_section = f"{num}. {section_match.group('name')}"
            current_subsection = ""
            continue

        subsection_match = SUBSECTION_PATTERN.match(line)
        if subsection_match:
            num = line.lstrip("#").strip().split(" ", 1)[0]
            current_subsection = f"{num} {subsection_match.group('name')}"
            continue

        req_match = REQ_PATTERN.match(line.strip())
        if req_match:
            req_id = req_match.group("id")
            summary = req_match.group("summary").rstrip(".")
            # Truncate long summaries for the JSON metadata
            if len(summary) > 80:
                summary = summary[:77] + "..."
            requirements[req_id] = {
                "section": current_section,
                "subsection": current_subsection,
                "summary": summary,
            }

    return requirements


def sync(dry_run: bool = False) -> None:
    if not MD_PATH.exists():
        print(f"Error: {MD_PATH} not found", file=sys.stderr)
        sys.exit(1)

    # Parse current markdown
    md_reqs = parse_markdown(MD_PATH)

    # Load existing JSON (if any)
    existing: dict[str, dict] = {}
    if JSON_PATH.exists():
        existing = json.loads(JSON_PATH.read_text())

    md_ids = set(md_reqs.keys())
    json_ids = set(existing.keys())

    added = sorted(md_ids - json_ids)
    removed = sorted(json_ids - md_ids)
    kept = sorted(md_ids & json_ids)

    # Build updated JSON
    updated: dict[str, dict] = {}
    for req_id in sorted(md_reqs.keys()):
        meta = md_reqs[req_id]
        if req_id in existing:
            # Preserve implement/enable flags, refresh metadata
            updated[req_id] = {
                "section": meta["section"],
                "subsection": meta["subsection"],
                "summary": meta["summary"],
                "implement": existing[req_id].get("implement", "N"),
                "enable": existing[req_id].get("enable", "N"),
            }
        else:
            updated[req_id] = {
                "section": meta["section"],
                "subsection": meta["subsection"],
                "summary": meta["summary"],
                "implement": "N",
                "enable": "N",
            }

    # Report
    print(f"Markdown requirements: {len(md_reqs)}")
    print(f"Existing JSON entries: {len(existing)}")
    print(f"  Added:   {len(added)}")
    print(f"  Removed: {len(removed)}")
    print(f"  Kept:    {len(kept)}")

    if added:
        print("\n  New requirements:")
        for req_id in added:
            print(f"    + {req_id}: {md_reqs[req_id]['summary']}")

    if removed:
        print("\n  Removed requirements:")
        for req_id in removed:
            flags = f"implement={existing[req_id].get('implement', 'N')}, enable={existing[req_id].get('enable', 'N')}"
            print(f"    - {req_id} ({flags})")

    # Check for metadata changes on kept entries
    metadata_changes = 0
    for req_id in kept:
        old = existing[req_id]
        new = updated[req_id]
        if (old.get("section") != new["section"]
                or old.get("subsection") != new["subsection"]
                or old.get("summary") != new["summary"]):
            metadata_changes += 1

    if metadata_changes:
        print(f"\n  Metadata refreshed: {metadata_changes} entries")

    if dry_run:
        print(f"\nDry run — no changes written to {JSON_PATH}")
    else:
        JSON_PATH.write_text(json.dumps(updated, indent=2) + "\n")
        print(f"\nWrote {len(updated)} entries to {JSON_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description="Sync controller JSON from requirements markdown."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing the file.",
    )
    args = parser.parse_args()
    sync(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
