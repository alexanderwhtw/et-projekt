"""Stereo rectification: aligns epipolar lines to image rows.

Pure logic: operates on already-known per-camera intrinsics and stereo
extrinsics (calibration.intrinsics.calibrate_intrinsics(),
calibration.extrinsics.calibrate_extrinsics()). No file I/O.

The P_L, P_R projection matrices compute_rectification() returns are
exactly what localization.stereo_depth.triangulate_matches() expects.
"""

import cv2
import numpy as np


def compute_rectification(
    K_L: np.ndarray,
    dist_L: np.ndarray,
    K_R: np.ndarray,
    dist_R: np.ndarray,
    image_size: tuple[int, int],
    R: np.ndarray,
    T: np.ndarray,
    alpha: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute stereo rectification transforms (cv2.stereoRectify).

    Args:
        K_L, dist_L, K_R, dist_R: per-camera intrinsics.
        image_size: (width, height) in pixels.
        R, T: left-to-right camera transform (extrinsics.calibrate_extrinsics()).
        alpha: 0 = crop to only valid pixels (no black borders), 1 = keep
            all pixels (black borders included). The ~2.25 deg roll
            misalignment of the current prototype rig costs ~2-3% image
            area at the edges after rectification (see docs/decisions.md,
            2026-09-02).

    Returns:
        R1, R2: (3, 3) rectifying rotations for the left/right camera.
        P1, P2: (3, 4) rectified projection matrices -- directly usable as
            P_L, P_R in localization.stereo_depth.triangulate_matches().
        Q: (4, 4) disparity-to-depth mapping matrix.
    """
    R1, R2, P1, P2, Q, _roi1, _roi2 = cv2.stereoRectify(
        K_L, dist_L, K_R, dist_R, image_size, R, np.asarray(T, dtype=np.float64).reshape(3, 1),
        flags=cv2.CALIB_ZERO_DISPARITY, alpha=alpha,
    )
    return R1, R2, P1, P2, Q


def compute_rectification_maps(
    K: np.ndarray,
    dist: np.ndarray,
    R_rect: np.ndarray,
    P_rect: np.ndarray,
    image_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel remap tables for one camera (cv2.initUndistortRectifyMap).

    Args:
        K, dist: that camera's intrinsics.
        R_rect: that camera's rectifying rotation (R1 or R2 from compute_rectification()).
        P_rect: that camera's rectified projection matrix (P1 or P2).
        image_size: (width, height) in pixels.

    Returns:
        map_x, map_y: remap tables for cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR).
    """
    return cv2.initUndistortRectifyMap(K, dist, R_rect, P_rect[:, :3], image_size, cv2.CV_32FC1)
