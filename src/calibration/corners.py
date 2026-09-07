"""Checkerboard corner detection and 3D object point generation.

Pure logic: operates on an already-loaded image, no file I/O.
"""

import cv2
import numpy as np


def find_checkerboard_corners(image: np.ndarray, pattern_size: tuple[int, int]) -> np.ndarray | None:
    """Detect subpixel-accurate inner checkerboard corners.

    Args:
        image: grayscale or BGR image.
        pattern_size: (cols, rows) number of INNER corners (e.g. (6, 7) for
            the project's asymmetric board, see docs/decisions.md, 2026-09-04).

    Returns:
        (cols*rows, 2) float32 array of corner pixel coordinates, in a
        consistent raster order (row by row) -- but not necessarily
        starting top-left or scanning left-to-right; only consistency
        across detections of the same physical board matters for
        calibration. Returns None if the pattern was not found.
        CALIB_CB_FAST_CHECK is deliberately not used: it produces false
        negatives on large/tilted boards (see docs/decisions.md, 2026-09-03,
        and cal/check_corners.py).
    """
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    found, corners = cv2.findChessboardCornersSB(image, pattern_size, flags=cv2.CALIB_CB_EXHAUSTIVE)
    return corners if found else None


def generate_object_points(pattern_size: tuple[int, int], square_size: float) -> np.ndarray:
    """3D object points of the checkerboard's inner corners, in the board's
    own coordinate frame (planar, Z=0), scaled to real-world units.

    Args:
        pattern_size: (cols, rows) number of inner corners.
        square_size: physical edge length of one square (e.g. meters).

    Returns:
        (cols*rows, 3) float32 array, in raster order (row by row). Serves
        as the object-point template paired index-for-index with
        find_checkerboard_corners()'s output -- the object frame's absolute
        orientation is arbitrary (calibration solves for the board's pose
        per image), only consistent per-index pairing matters.
    """
    cols, rows = pattern_size
    object_points = np.zeros((cols * rows, 3), dtype=np.float32)
    object_points[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_size
    return object_points
