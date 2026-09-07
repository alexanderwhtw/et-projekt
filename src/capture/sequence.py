"""Indexed stereo-pair capture sequences: file naming and manifest bookkeeping.

Filesystem I/O, deliberately separate from camera.py's hardware trigger --
shared by calibration image capture and VO sequence capture (same
left_NNN.png/right_NNN.png + manifest.csv convention, see
docs/decisions.md, 2026-09-04).
"""

import csv
from pathlib import Path


def build_frame_paths(directory: Path, index: int) -> tuple[Path, Path]:
    """left_NNN.png / right_NNN.png paths for a given index (3-digit
    zero-padded), see docs/decisions.md, 2026-09-04."""
    directory = Path(directory)
    return directory / f"left_{index:03d}.png", directory / f"right_{index:03d}.png"


def next_free_index(directory: Path) -> int:
    """Smallest index >= 0 not yet used by an existing left_NNN.png in
    `directory` -- lets a capture session resume/extend an existing set
    without overwriting prior frames."""
    directory = Path(directory)
    used_indices = set()
    for path in directory.glob("left_*.png"):
        try:
            used_indices.add(int(path.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue

    index = 0
    while index in used_indices:
        index += 1
    return index


def append_manifest_row(
    directory: Path, row: dict, fieldnames: list[str], manifest_filename: str = "manifest.csv"
) -> None:
    """Append one row to the manifest CSV, writing the header first if the
    file doesn't exist yet."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / manifest_filename
    is_new = not manifest_path.is_file()

    with open(manifest_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
