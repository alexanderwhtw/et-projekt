"""Stereo feature matching and triangulation for one frame.

Pure logic: works on keypoints/descriptors already detected by
`features.detect_features()` and on projection matrices already computed by
calibration (`cv2.stereoRectify`). No file or camera I/O.

Assumes rectified input images: epipolar lines are horizontal, so a valid
L/R correspondence lies on (nearly) the same image row and has positive
disparity (x_L > x_R, left camera is the reference).
"""

from typing import Sequence

import cv2
import numpy as np


def match_stereo_pairs(
    keypoints_L: Sequence[cv2.KeyPoint],
    descriptors_L: np.ndarray,
    keypoints_R: Sequence[cv2.KeyPoint],
    descriptors_R: np.ndarray,
    max_y_diff: float = 2.0,
) -> list[cv2.DMatch]:
    """Match ORB descriptors between rectified left/right images.

    Args:
        keypoints_L, descriptors_L: output of detect_features() on the left image.
        keypoints_R, descriptors_R: output of detect_features() on the right image.
        max_y_diff: max allowed row offset (px) for a valid match, to allow
            for residual rectification error.

    Returns:
        Matches (queryIdx into L, trainIdx into R) that satisfy the
        epipolar/disparity constraints, sorted by descriptor distance
        (best first).
    """
    if len(descriptors_L) == 0 or len(descriptors_R) == 0:
        return []

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    raw_matches = matcher.match(descriptors_L, descriptors_R)

    filtered = []
    for m in raw_matches:
        x_L, y_L = keypoints_L[m.queryIdx].pt
        x_R, y_R = keypoints_R[m.trainIdx].pt
        if abs(y_L - y_R) > max_y_diff:
            continue
        if x_L <= x_R:
            continue
        filtered.append(m)

    filtered.sort(key=lambda m: m.distance)
    return filtered


def triangulate_matches(
    keypoints_L: Sequence[cv2.KeyPoint],
    keypoints_R: Sequence[cv2.KeyPoint],
    matches: Sequence[cv2.DMatch],
    P_L: np.ndarray,
    P_R: np.ndarray,
) -> np.ndarray:
    """Triangulate matched keypoint pairs into 3D points.

    Args:
        keypoints_L, keypoints_R: detected keypoints in the left/right image.
        matches: correspondences from match_stereo_pairs().
        P_L, P_R: 3x4 rectified projection matrices (from cv2.stereoRectify).

    Returns:
        (N, 3) array of 3D points in the left camera's coordinate frame,
        same order as `matches`.
    """
    if not matches:
        return np.empty((0, 3), dtype=np.float64)

    pts_L = np.array([keypoints_L[m.queryIdx].pt for m in matches], dtype=np.float64).T
    pts_R = np.array([keypoints_R[m.trainIdx].pt for m in matches], dtype=np.float64).T

    points_4d = cv2.triangulatePoints(P_L, P_R, pts_L, pts_R)
    return (points_4d[:3] / points_4d[3]).T
