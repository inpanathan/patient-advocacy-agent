"""Generate narration WAV files for each demo scene using Piper TTS."""
# ruff: noqa: T201 — CLI script, print is intentional

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path


def get_wav_duration(path: Path) -> float:
    """Return duration of a WAV file in seconds."""
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def main() -> None:
    demo_dir = Path(__file__).resolve().parent.parent
    project_root = demo_dir.parent
    config_path = demo_dir / "config.json"

    with open(config_path) as f:
        config = json.load(f)

    piper_model = project_root / config["piper"]["model"]
    output_dir = demo_dir / "output" / "narration"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not piper_model.exists():
        print(f"ERROR: Piper model not found at {piper_model}")
        print("Install with: scripts/setup.sh or download manually")
        raise SystemExit(1)

    timing: dict[str, float] = {}

    for scene in config["scenes"]:
        scene_id = scene["id"]
        text = scene["narration"]
        out_wav = output_dir / f"{scene_id}.wav"

        print(f"Generating narration for {scene_id}...")

        result = subprocess.run(
            [
                "piper",
                "--model",
                str(piper_model),
                "--output_file",
                str(out_wav),
            ],
            input=text,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"ERROR generating {scene_id}: {result.stderr}")
            raise SystemExit(1)

        duration = get_wav_duration(out_wav)
        timing[scene_id] = round(duration, 2)
        print(f"  {scene_id}: {duration:.1f}s -> {out_wav.name}")

    timing_path = output_dir / "timing.json"
    with open(timing_path, "w") as f:
        json.dump(timing, f, indent=2)

    total = sum(timing.values())
    print(f"\nTotal narration: {total:.1f}s")
    print(f"Timing written to {timing_path}")


if __name__ == "__main__":
    main()
