"""Ties camera.py (hardware trigger) and sequence.py (naming/manifest)
together into a single "capture the next indexed stereo pair" call.

Used by both calibration image capture and VO sequence capture -- same
underlying operation, different output directory and manifest fields.
"""

from datetime import datetime
from pathlib import Path

import cv2

from . import camera
from .sequence import append_manifest_row, build_frame_paths, next_free_index


def capture_indexed_pair(
    directory: Path,
    shutter_us: int,
    gain: float,
    manifest_fieldnames: list[str],
    extra_manifest_fields: dict | None = None,
    **camera_kwargs,
) -> int:
    """Capture one stereo pair at the next free index in `directory`.

    Triggers a capture (camera.capture_frame), splits it into
    left_NNN.png/right_NNN.png (camera.split_stereo_frame), and appends a
    manifest row with the given metadata plus index/shutter/gain/timestamp.

    Args:
        directory: destination folder (e.g. data/calibration_images/).
        shutter_us, gain: exposure settings, see camera.build_capture_command().
        manifest_fieldnames: full column list for the manifest CSV --
            must include "index", "shutter", "gain", "timestamp" plus
            whatever extra_manifest_fields provides.
        extra_manifest_fields: additional manifest columns for this row
            (e.g. {"distanz_m": 1.0, "notiz": "frontal"}).
        **camera_kwargs: forwarded to camera.capture_frame() (awb_gains,
            denoise, width, height, timeout_ms).

    Returns:
        The index used for this pair.
    """
    directory = Path(directory)
    index = next_free_index(directory)
    left_path, right_path = build_frame_paths(directory, index)

    combined_path = directory / f".combined_{index:03d}.png"
    camera.capture_frame(combined_path, shutter_us, gain, **camera_kwargs)
    combined_image = cv2.imread(str(combined_path), cv2.IMREAD_GRAYSCALE)
    left, right = camera.split_stereo_frame(combined_image)
    cv2.imwrite(str(left_path), left)
    cv2.imwrite(str(right_path), right)
    combined_path.unlink()

    row = {
        "index": index,
        "shutter": shutter_us,
        "gain": gain,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        **(extra_manifest_fields or {}),
    }
    append_manifest_row(directory, row, manifest_fieldnames)

    return index
