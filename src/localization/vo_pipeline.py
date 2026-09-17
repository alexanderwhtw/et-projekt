"""Orchestrates the visual odometry chain over a sequence of stereo frames.

Pure logic: takes already-loaded, already-rectified stereo image pairs and
calibration projection matrices, wires together detect_features ->
match_stereo_pairs -> triangulate_matches (per frame) and
match_temporal_features -> estimate_relative_pose (between consecutive
frames). No file or camera I/O -- loading images/calibration from disk is a
separate, later concern (src/capture, src/calibration).

Two layers, see docs/decisions.md (2026-09-16, Live-VO-Umstellung):
- init_vo_step()/step_vo_pipeline(): the incremental primitive, one new
  frame in, one new pose out, explicit state threaded through the return
  value (same pattern as src/capture/sequence.py's next_free_index() --
  no classes, caller owns the state). This is what a live capture loop will
  call once per captured frame.
- run_vo_pipeline(): batch convenience wrapper, a loop over the above, for
  offline sequences already fully captured (see scripts/run_vo_sequence.py).
  Implemented on top of the incremental primitive so batch and live
  processing cannot drift apart.
"""

from typing import Sequence

import numpy as np

from .features import detect_features
from .pose_estimation import estimate_relative_pose_ransac
from .stereo_depth import match_stereo_pairs, triangulate_matches
from .temporal_matching import match_temporal_features
from .trajectory import to_homogeneous


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


def init_vo_step(
    image_L: np.ndarray,
    image_R: np.ndarray,
    P_L: np.ndarray,
    P_R: np.ndarray,
    initial_pose: np.ndarray | None = None,
    n_features: int = 500,
    max_y_diff: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Initialize incremental VO state from the first stereo frame.

    Args:
        image_L, image_R: first (rectified) stereo frame.
        P_L, P_R: 3x4 rectified projection matrices (from cv2.stereoRectify).
        initial_pose: 4x4 pose to anchor the trajectory to (the vermessene
            Startpunkt, see data/reference_points.yaml). Defaults to the
            identity (origin).
        n_features, max_y_diff: see extract_frame_points().

    Returns:
        (pose, points_3d, descriptors) state, to be passed into the first
        step_vo_pipeline() call as prev_pose/prev_points/prev_descriptors.
    """
    pose = np.eye(4) if initial_pose is None else np.asarray(initial_pose, dtype=np.float64)
    points_3d, descriptors = extract_frame_points(image_L, image_R, P_L, P_R, n_features, max_y_diff)
    return pose, points_3d, descriptors


def step_vo_pipeline(
    image_L: np.ndarray,
    image_R: np.ndarray,
    P_L: np.ndarray,
    P_R: np.ndarray,
    prev_pose: np.ndarray,
    prev_points: np.ndarray,
    prev_descriptors: np.ndarray,
    n_features: int = 500,
    max_y_diff: float = 2.0,
    ratio_threshold: float = 0.75,
    min_temporal_matches: int = 3,
    ransac_inlier_threshold: float = 0.02,
    ransac_iterations: int = 200,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Process one new stereo frame against the previous frame's VO state.

    This is the incremental primitive a live capture loop calls once per
    newly captured frame (see docs/decisions.md, 2026-09-16). run_vo_pipeline()
    is a batch loop built on top of this for already-captured sequences.

    Args:
        image_L, image_R: new (rectified) stereo frame.
        P_L, P_R: 3x4 rectified projection matrices.
        prev_pose: previous frame's absolute 4x4 pose (from init_vo_step()
            or a prior step_vo_pipeline() call).
        prev_points, prev_descriptors: previous frame's triangulated points
            and descriptors (from init_vo_step() or a prior
            step_vo_pipeline() call).
        n_features, max_y_diff: see extract_frame_points().
        ratio_threshold: see match_temporal_features().
        min_temporal_matches: minimum number of temporal correspondences
            required to estimate a relative pose.
        ransac_inlier_threshold, ransac_iterations: see
            estimate_relative_pose_ransac(). Stereo/temporal matching
            produces a non-trivial fraction of wrong correspondences even on
            well-behaved input (empirically ~39% on a synthetic test scene,
            see docs/decisions.md, 2026-09-07) -- pose estimation is RANSAC-
            based for that reason, not plain least-squares.
        seed: RNG seed forwarded to RANSAC sampling, for reproducible runs
            (tests). None = nondeterministic.

    Returns:
        (pose, points_3d, descriptors) -- the new absolute pose, and the new
        state to pass into the next step_vo_pipeline() call.

    Raises:
        RuntimeError: fewer than min_temporal_matches valid temporal
            correspondences to the previous frame, or RANSAC couldn't find
            a rigid pose with at least 3 inliers among the matches (see
            estimate_relative_pose_ransac()) -- the pipeline stops rather
            than silently produce an unreliable pose (no loop-closure/
            correction exists to fix it later, see docs/decisions.md,
            2026-09-04).
    """
    points_curr, descriptors_curr = extract_frame_points(image_L, image_R, P_L, P_R, n_features, max_y_diff)

    temporal_matches = match_temporal_features(prev_descriptors, descriptors_curr, ratio_threshold)
    if len(temporal_matches) < min_temporal_matches:
        raise RuntimeError(
            f"only {len(temporal_matches)} temporal matches (< {min_temporal_matches}) -- "
            "cannot estimate relative pose"
        )

    matched_prev = prev_points[[m.queryIdx for m in temporal_matches]]
    matched_curr = points_curr[[m.trainIdx for m in temporal_matches]]
    R, t, _inlier_mask = estimate_relative_pose_ransac(
        matched_prev, matched_curr, ransac_inlier_threshold, ransac_iterations, seed
    )

    pose = prev_pose @ to_homogeneous(R, t)
    return pose, points_curr, descriptors_curr


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
    """Run the VO chain over a sequence of already-captured stereo frames.

    Batch convenience wrapper around init_vo_step()/step_vo_pipeline() (see
    module docstring) for offline sequences -- a live capture loop should
    call those directly instead, one frame at a time.

    Args:
        stereo_frames: (image_L, image_R) pairs, in temporal order,
            already rectified.
        P_L, P_R, initial_pose, n_features, max_y_diff, ratio_threshold,
        min_temporal_matches, ransac_inlier_threshold, ransac_iterations,
        seed: see init_vo_step()/step_vo_pipeline().

    Returns:
        List of len(stereo_frames) absolute 4x4 poses, one per frame.

    Raises:
        ValueError: no frames given.
        RuntimeError: a consecutive frame pair has fewer than
            min_temporal_matches valid temporal correspondences (see
            step_vo_pipeline()).
    """
    if not stereo_frames:
        raise ValueError("need at least 1 stereo frame")

    pose, points, descriptors = init_vo_step(*stereo_frames[0], P_L, P_R, initial_pose, n_features, max_y_diff)
    poses = [pose]

    for frame_index, (image_L, image_R) in enumerate(stereo_frames[1:], start=1):
        try:
            pose, points, descriptors = step_vo_pipeline(
                image_L,
                image_R,
                P_L,
                P_R,
                pose,
                points,
                descriptors,
                n_features,
                max_y_diff,
                ratio_threshold,
                min_temporal_matches,
                ransac_inlier_threshold,
                ransac_iterations,
                seed,
            )
        except RuntimeError as e:
            raise RuntimeError(f"frame {frame_index}: {e}") from e
        poses.append(pose)

    return poses
