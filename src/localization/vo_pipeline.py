"""Orchestrates the visual odometry chain over a sequence of stereo frames.

Pure logic: takes already-loaded, already-rectified stereo image pairs and
calibration projection matrices, wires together detect_features ->
match_stereo_pairs -> triangulate_matches (per frame) and
match_temporal_features -> estimate_relative_pose (between consecutive
frames) -> chain_poses. No file or camera I/O -- loading images/calibration
from disk is a separate, later concern (src/capture, src/calibration).
"""

from typing import Sequence

import numpy as np

from .features import detect_features
from .pose_estimation import estimate_relative_pose_ransac
from .stereo_depth import match_stereo_pairs, triangulate_matches
from .temporal_matching import match_temporal_features
from .trajectory import chain_poses


def extract_frame_points(
    image_L: np.ndarray,
    image_R: np.ndarray,
    P_L: np.ndarray,
    P_R: np.ndarray,
    n_features: int = 500,
    max_y_diff: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Detect, stereo-match and triangulate features in one stereo frame.

    Returns:
        points_3d: (N, 3) triangulated points in the left camera frame.
        descriptors: (N, 32) descriptor of each point's left keypoint, same
            order/index as points_3d -- carries the point's "identity" for
            temporal matching against the next frame.
    """
    keypoints_L, descriptors_L = detect_features(image_L, n_features)
    keypoints_R, descriptors_R = detect_features(image_R, n_features)
    matches = match_stereo_pairs(keypoints_L, descriptors_L, keypoints_R, descriptors_R, max_y_diff)

    points_3d = triangulate_matches(keypoints_L, keypoints_R, matches, P_L, P_R)
    if matches:
        descriptors = descriptors_L[[m.queryIdx for m in matches]]
    else:
        descriptors = np.empty((0, 32), dtype=np.uint8)

    return points_3d, descriptors


def run_vo_pipeline(
    stereo_frames: Sequence[tuple[np.ndarray, np.ndarray]],
    P_L: np.ndarray,
    P_R: np.ndarray,
    initial_pose: np.ndarray | None = None,
    n_features: int = 500,
    max_y_diff: float = 2.0,
    ratio_threshold: float = 0.75,
    min_temporal_matches: int = 3,
    ransac_inlier_threshold: float = 0.02,
    ransac_iterations: int = 200,
    seed: int | None = None,
) -> list[np.ndarray]:
    """Run the VO chain over a sequence of stereo frames.

    Args:
        stereo_frames: (image_L, image_R) pairs, in temporal order,
            already rectified.
        P_L, P_R: 3x4 rectified projection matrices (from cv2.stereoRectify).
        initial_pose: 4x4 pose to anchor the trajectory to (the vermessene
            Startpunkt, see data/reference_points.yaml). Defaults to the
            identity (origin).
        n_features, max_y_diff: see extract_frame_points().
        ratio_threshold: see match_temporal_features().
        min_temporal_matches: minimum number of temporal correspondences
            required to estimate a relative pose for a frame pair.
        ransac_inlier_threshold, ransac_iterations: see
            estimate_relative_pose_ransac(). Stereo/temporal matching
            produces a non-trivial fraction of wrong correspondences even on
            well-behaved input (empirically ~39% on a synthetic test scene,
            see docs/decisions.md, 2026-09-07) -- pose estimation is RANSAC-
            based for that reason, not plain least-squares.
        seed: RNG seed forwarded to RANSAC sampling, for reproducible runs
            (tests). None = nondeterministic.

    Returns:
        List of len(stereo_frames) absolute 4x4 poses, one per frame.

    Raises:
        ValueError: no frames given.
        RuntimeError: a consecutive frame pair has fewer than
            min_temporal_matches valid temporal correspondences -- the
            pipeline stops rather than silently produce an unreliable pose
            (no loop-closure/correction exists to fix it later, see
            docs/decisions.md, 2026-09-04).
    """
    if not stereo_frames:
        raise ValueError("need at least 1 stereo frame")

    points_prev, descriptors_prev = extract_frame_points(*stereo_frames[0], P_L, P_R, n_features, max_y_diff)

    relative_poses = []
    for frame_index, (image_L, image_R) in enumerate(stereo_frames[1:], start=1):
        points_curr, descriptors_curr = extract_frame_points(image_L, image_R, P_L, P_R, n_features, max_y_diff)

        temporal_matches = match_temporal_features(descriptors_prev, descriptors_curr, ratio_threshold)
        if len(temporal_matches) < min_temporal_matches:
            raise RuntimeError(
                f"frame {frame_index}: only {len(temporal_matches)} temporal matches "
                f"(< {min_temporal_matches}) -- cannot estimate relative pose"
            )

        matched_prev = points_prev[[m.queryIdx for m in temporal_matches]]
        matched_curr = points_curr[[m.trainIdx for m in temporal_matches]]
        R, t, _inlier_mask = estimate_relative_pose_ransac(
            matched_prev, matched_curr, ransac_inlier_threshold, ransac_iterations, seed
        )
        relative_poses.append((R, t))

        points_prev, descriptors_prev = points_curr, descriptors_curr

    return chain_poses(relative_poses, initial_pose)
