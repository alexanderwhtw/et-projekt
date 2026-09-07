"""Intrinsic camera calibration (per-camera K, distortion coefficients).

Pure logic: operates on already-detected corner correspondences
(corners.find_checkerboard_corners() + corners.generate_object_points()),
no file I/O.
"""

import cv2
import numpy as np


def calibrate_intrinsics(
    object_points_list: list[np.ndarray],
    image_points_list: list[np.ndarray],
    image_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, float]:
    """Estimate a single camera's intrinsic matrix and distortion coefficients.

    Args:
        object_points_list: one (N, 3) float32 array of checkerboard object
            points per calibration image (typically the same
            corners.generate_object_points() result, repeated).
        image_points_list: one (N, 2) float32 array of detected corners per
            image (corners.find_checkerboard_corners()), same order and
            length as object_points_list.
        image_size: (width, height) in pixels -- OpenCV's (cols, rows)
            convention, the reverse of numpy's image.shape.

    Returns:
        K: (3, 3) camera matrix.
        dist: (1, 5) distortion coefficients (k1, k2, p1, p2, k3).
        reprojection_error: RMS reprojection error (px) over all images -- a
            rough calibration-quality indicator, see scripts/check_calibration.py.
    """
    if len(object_points_list) != len(image_points_list):
        raise ValueError(
            "object_points_list and image_points_list must have the same length, "
            f"got {len(object_points_list)} and {len(image_points_list)}"
        )

    reprojection_error, K, dist, _rvecs, _tvecs = cv2.calibrateCamera(
        object_points_list, image_points_list, image_size, None, None
    )
    return K, dist, reprojection_error


def compute_per_image_reprojection_errors(
    object_points_list: list[np.ndarray],
    image_points_list: list[np.ndarray],
    K: np.ndarray,
    dist: np.ndarray,
) -> np.ndarray:
    """Per-image RMS reprojection error (px) for an already-calibrated camera.

    Re-solves each image's pose (cv2.solvePnP) against the given K/dist,
    then compares projected object points to the detected corners.
    calibrate_intrinsics() only returns the overall RMS error -- this is
    useful to spot individual bad calibration images (see
    scripts/check_calibration.py).

    Returns:
        (n_images,) array of per-image RMS reprojection error in pixels.
    """
    errors = np.empty(len(object_points_list))
    for i, (object_points, image_points) in enumerate(zip(object_points_list, image_points_list)):
        _, rvec, tvec = cv2.solvePnP(object_points, image_points, K, dist)
        projected, _ = cv2.projectPoints(object_points, rvec, tvec, K, dist)
        residuals = projected.reshape(-1, 2) - image_points
        errors[i] = np.sqrt(np.mean(np.sum(residuals**2, axis=1)))
    return errors
