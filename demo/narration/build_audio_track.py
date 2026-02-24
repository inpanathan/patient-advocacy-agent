"""Concatenate per-scene narration WAVs with silence gaps into a single audio track."""
# ruff: noqa: T201 — CLI script, print is intentional

from __future__ import annotations

import json
import struct
import wave
from pathlib import Path


def create_silence_wav(path: Path, duration_sec: float, sample_rate: int = 22050) -> None:
    """Create a silent WAV file of the given duration."""
    n_frames = int(sample_rate * duration_sec)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


def read_wav_frames(path: Path) -> tuple[bytes, wave._wave_params]:
    """Read all frames from a WAV file. Returns (frames_bytes, params)."""
    with wave.open(str(path), "rb") as wf:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())
    return frames, params


def main() -> None:
    demo_dir = Path(__file__).resolve().parent.parent
    config_path = demo_dir / "config.json"
    narration_dir = demo_dir / "output" / "narration"
    timing_path = narration_dir / "timing.json"
    output_path = demo_dir / "output" / "narration_combined.wav"

    with open(config_path) as f:
        config = json.load(f)

    with open(timing_path) as f:
        timing = json.load(f)

    scenes = config["scenes"]

    # Determine sample rate from first scene
    first_wav = narration_dir / f"{scenes[0]['id']}.wav"
    with wave.open(str(first_wav), "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        samp_width = wf.getsampwidth()

    print(f"Audio format: {sample_rate}Hz, {n_channels}ch, {samp_width * 8}bit")

    # Build combined track: for each scene, add silence gap then narration
    all_frames = b""
    current_time = 0.0

    for scene in scenes:
        scene_id = scene["id"]
        target_start = scene["start_sec"]
        narration_duration = timing[scene_id]
        wav_path = narration_dir / f"{scene_id}.wav"

        # Add silence to reach the target start time
        gap = target_start - current_time
        if gap > 0.1:
            n_silence_frames = int(sample_rate * gap)
            silence = struct.pack(
                f"<{n_silence_frames * n_channels}h", *([0] * (n_silence_frames * n_channels))
            )
            all_frames += silence
            current_time += gap
            print(f"  Silence: {gap:.1f}s (to reach {target_start}s)")

        # Add narration
        frames, _ = read_wav_frames(wav_path)
        all_frames += frames
        current_time += narration_duration
        print(f"  {scene_id}: {narration_duration:.1f}s (ends at {current_time:.1f}s)")

    # Add 1 second of trailing silence
    trailing = int(sample_rate * 1.0)
    all_frames += struct.pack(f"<{trailing * n_channels}h", *([0] * (trailing * n_channels)))

    # Write combined file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(samp_width)
        wf.setframerate(sample_rate)
        wf.writeframes(all_frames)

    total_duration = len(all_frames) / (sample_rate * n_channels * samp_width)
    print(f"\nCombined track: {total_duration:.1f}s -> {output_path}")


if __name__ == "__main__":
    main()
