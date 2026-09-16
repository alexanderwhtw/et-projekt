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


def compute_disparity_map(
    image_L: np.ndarray,
    image_R: np.ndarray,
    num_disparities: int = 64,
    block_size: int = 9,
) -> np.ndarray:
    """Dense disparity map via Semi-Global Block Matching (cv2.StereoSGBM).

    Illustrative only -- the VO pipeline uses sparse ORB features + the
    stereo matching/triangulation above, not this dense map (see
    scripts/check_disparity.py, docs/decisions.md 2026-09-16: an
    additional visualization for the written thesis, listed in CLAUDE.md's
    original sanity-check roadmap, not part of the localization algorithm).

    Args:
        image_L, image_R: rectified grayscale stereo pair (horizontal
            epipolar lines).
        num_disparities: max disparity search range in px, must be a
            positive multiple of 16 (cv2.StereoSGBM requirement).
        block_size: matched block size (odd, >=3).

    Returns:
        (H, W) float32 disparity map in pixels. Pixels with no valid match
        (e.g. textureless regions) are NaN.

    Raises:
        ValueError: num_disparities is not a positive multiple of 16.
    """
    if num_disparities <= 0 or num_disparities % 16 != 0:
        raise ValueError(f"num_disparities must be a positive multiple of 16, got {num_disparities}")

    matcher = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=num_disparities,
        blockSize=block_size,
        P1=8 * block_size**2,
        P2=32 * block_size**2,
    )
    # cv2 returns a 16x fixed-point int16 map; negative values mark
    # no-match/invalid pixels (see cv2.StereoSGBM docs)
    raw = matcher.compute(image_L, image_R).astype(np.float32) / 16.0
    raw[raw < 0] = np.nan
    return raw
