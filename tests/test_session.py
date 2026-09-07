import csv
from unittest.mock import patch

import cv2
import numpy as np

from src.capture.session import capture_indexed_pair


def _fake_capture_frame(output_path, shutter_us, gain, **kwargs):
    """Stand-in for camera.capture_frame(): writes a synthetic combined
    frame instead of calling rpicam-still (no camera hardware in tests)."""
    left_half = np.full((50, 60), 10, dtype=np.uint8)
    right_half = np.full((50, 60), 200, dtype=np.uint8)
    cv2.imwrite(str(output_path), np.hstack([left_half, right_half]))
    return output_path


def test_capture_indexed_pair_writes_split_images_and_manifest_row(tmp_path):
    fieldnames = ["index", "distanz_m", "notiz", "shutter", "gain", "timestamp"]

    with patch("src.capture.session.camera.capture_frame", side_effect=_fake_capture_frame):
        index = capture_indexed_pair(
            tmp_path, shutter_us=10000, gain=1.0, manifest_fieldnames=fieldnames,
            extra_manifest_fields={"distanz_m": 1.0, "notiz": "frontal"},
        )

    assert index == 0
    left_path, right_path = tmp_path / "left_000.png", tmp_path / "right_000.png"
    assert left_path.is_file()
    assert right_path.is_file()
    assert not (tmp_path / ".combined_000.png").exists()  # temp combined file cleaned up

    left = cv2.imread(str(left_path), cv2.IMREAD_GRAYSCALE)
    right = cv2.imread(str(right_path), cv2.IMREAD_GRAYSCALE)
    assert left.shape == (50, 60)
    np.testing.assert_array_equal(left, np.full((50, 60), 10, dtype=np.uint8))
    np.testing.assert_array_equal(right, np.full((50, 60), 200, dtype=np.uint8))

    with open(tmp_path / "manifest.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["index"] == "0"
    assert rows[0]["notiz"] == "frontal"
    assert rows[0]["shutter"] == "10000"


def test_capture_indexed_pair_uses_next_free_index(tmp_path):
    fieldnames = ["index", "shutter", "gain", "timestamp"]
    (tmp_path / "left_000.png").touch()

    with patch("src.capture.session.camera.capture_frame", side_effect=_fake_capture_frame):
        index = capture_indexed_pair(tmp_path, shutter_us=10000, gain=1.0, manifest_fieldnames=fieldnames)

    assert index == 1
    assert (tmp_path / "left_001.png").is_file()
