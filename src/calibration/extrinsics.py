"""Stereo extrinsic calibration: rigid transform between the two cameras.

Pure logic: operates on already-detected corner correspondences and
already-known per-camera intrinsics (calibration.intrinsics.calibrate_intrinsics()),
no file I/O.
"""

import cv2
import numpy as np


def calibrate_extrinsics(
    object_points_list: list[np.ndarray],
    image_points_L_list: list[np.ndarray],
    image_points_R_list: list[np.ndarray],
    K_L: np.ndarray,
    dist_L: np.ndarray,
    K_R: np.ndarray,
    dist_R: np.ndarray,
    image_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, float]:
    """Estimate the rigid transform from the left to the right camera.

    Wraps cv2.stereoCalibrate with CALIB_FIX_INTRINSIC: K_L/dist_L/K_R/dist_R
    are taken as already known (from calibrate_intrinsics()) and held fixed,
    only the relative pose is solved for.

    Args:
        object_points_list: one (N, 3) checkerboard object-points array per
            stereo pair (same physical board, so typically the same
            corners.generate_object_points() result repeated).
        image_points_L_list, image_points_R_list: detected corners
            (corners.find_checkerboard_corners()) in the left/right image,
            one per stereo pair, index-matched with object_points_list.
        K_L, dist_L, K_R, dist_R: per-camera intrinsics.
        image_size: (width, height) in pixels.

    Returns:
        R: (3, 3) rotation, left camera frame -> right camera frame.
        T: (3,) translation, left camera frame -> right camera frame (same
            units as the square_size used to build object_points_list, e.g.
            meters -- norm(T) should be close to the physically measured
            baseline of 60mm, see docs/decisions.md, 2026-09-02).
        reprojection_error: RMS stereo reprojection error (px).
    """
    reprojection_error, _K_L, _dist_L, _K_R, _dist_R, R, T, _E, _F = cv2.stereoCalibrate(
        object_points_list,
        image_points_L_list,
        image_points_R_list,
        K_L,
        dist_L,
        K_R,
        dist_R,
        image_size,
        flags=cv2.CALIB_FIX_INTRINSIC,
    )
    return R, T.reshape(3), reprojection_error
