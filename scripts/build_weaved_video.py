#!/usr/bin/env python3
"""Stitch Colab-generated clips into a final synchronized Movin demo MP4.

Expected inputs:
  assets/video-manifest.json
  assets/clips/*.mp4          # each clip < 20 MB, created by Colab processor
  assets/generated/narration.mp3

Output:
  assets/generated/movin_martech_weaved.mp4
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "video-manifest.json"
SAMPLE_MANIFEST = ROOT / "assets" / "video-manifest.sample.json"
OUT_DIR = ROOT / "assets" / "generated"
SILENT_STITCH = OUT_DIR / "movin_martech_silent_stitch.mp4"
NARRATION = OUT_DIR / "narration.mp3"
FINAL = OUT_DIR / "movin_martech_weaved.mp4"
MAX_CLIP_MB = 20.0


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(out)


def ensure_ffmpeg() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    if missing:
        raise SystemExit(f"{', '.join(missing)} is required to build the final video.")


def load_manifest() -> dict:
    manifest_path = MANIFEST if MANIFEST.exists() else SAMPLE_MANIFEST
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = data.get("clips", [])
    if not clips:
        raise SystemExit("No clips found in video manifest.")
    return data


def validate_clips(clips: list[dict]) -> list[Path]:
    paths: list[Path] = []
    missing: list[str] = []
    too_large: list[str] = []
    for clip in clips:
        p = ROOT / clip["src"]
        if not p.exists():
            missing.append(str(p.relative_to(ROOT)))
            continue
        mb = p.stat().st_size / (1024 * 1024)
        if mb > MAX_CLIP_MB + 0.3:
            too_large.append(f"{p.relative_to(ROOT)} ({mb:.1f} MB)")
        paths.append(p)
    if missing:
        raise SystemExit("Missing clip files. Run the Colab processor and upload these paths:\n" + "\n".join(missing))
    if too_large:
        raise SystemExit("These clips are over 20 MB. Re-run Colab with a lower target size or higher CRF:\n" + "\n".join(too_large))
    return paths


def stitch_video(paths: list[Path]) -> None:
    """Use concat filter, not concat demuxer, so clips with different source timestamps still stitch correctly."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = ["ffmpeg", "-y"]
    for p in paths:
        cmd.extend(["-i", str(p)])

    chains = []
    labels = []
    for idx, _ in enumerate(paths):
        label = f"v{idx}"
        labels.append(f"[{label}]")
        chains.append(
            f"[{idx}:v]setpts=PTS-STARTPTS,"
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "fps=24,format=yuv420p"
            f"[{label}]"
        )
    chains.append("".join(labels) + f"concat=n={len(paths)}:v=1:a=0[v]")
    filter_complex = ";".join(chains)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "28",
        "-an", "-movflags", "+faststart", str(SILENT_STITCH)
    ])
    run(cmd)


def add_narration() -> None:
    if not NARRATION.exists():
        raise SystemExit("Narration MP3 missing. Run scripts/build_narration.py first.")

    video_duration = ffprobe_duration(SILENT_STITCH)
    narration_duration = ffprobe_duration(NARRATION)
    delta = narration_duration - video_duration
    filters = []
    if delta > 0.05:
        filters.append(f"tpad=stop_mode=clone:stop_duration={delta:.3f}")
    filters.append(f"trim=duration={narration_duration:.3f}")
    filters.append("setpts=PTS-STARTPTS")

    run([
        "ffmpeg", "-y", "-i", str(SILENT_STITCH), "-i", str(NARRATION),
        "-filter:v", ",".join(filters),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "28",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(FINAL)
    ])


def main() -> None:
    ensure_ffmpeg()
    data = load_manifest()
    paths = validate_clips(data["clips"])
    stitch_video(paths)
    add_narration()
    size_mb = FINAL.stat().st_size / (1024 * 1024)
    print(f"Created {FINAL.relative_to(ROOT)} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
