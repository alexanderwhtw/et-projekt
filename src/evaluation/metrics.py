"""Trajectory error metrics: ATE and RPE (see CLAUDE.md, Phase 3).

Pure logic: operates on plain position/rotation arrays already loaded from
trajectory.yaml / ground_truth.yaml. No file I/O (see scripts/evaluate_trajectory.py
for that).

Deliberately unaligned (no Umeyama/Horn rigid alignment before comparing, as
common in SLAM benchmarks like TUM RGB-D): the VO trajectory is anchored to a
measured start point and uses the same axis convention as the ground truth
(see data/vo_sequences/*/ground_truth.yaml), so estimated and ground-truth
positions already live in the same frame. Aligning them first would mask real
drift instead of measuring it. See docs/decisions.md (2026-09-16).
"""

import numpy as np


def _check_matching_length(estimated: np.ndarray, ground_truth: np.ndarray) -> None:
    if len(estimated) != len(ground_truth):
        raise ValueError(f"length mismatch: {len(estimated)} estimated vs {len(ground_truth)} ground-truth positions")


def absolute_trajectory_error(estimated: np.ndarray, ground_truth: np.ndarray) -> dict:
    """Per-frame Euclidean distance between estimated and ground-truth positions (ATE).

    Args:
        estimated: (N, 3) VO positions, e.g. positions_from_poses(chain_poses(...)).
        ground_truth: (N, 3) measured (Maßband) positions, same frame/order.

    Returns:
        dict with "per_frame" ((N,) array, meters), "rmse", "mean", "max"
        (all in meters).

    Raises:
        ValueError: estimated and ground_truth have different lengths.
    """
    estimated = np.asarray(estimated, dtype=np.float64)
    ground_truth = np.asarray(ground_truth, dtype=np.float64)
    _check_matching_length(estimated, ground_truth)

    per_frame = np.linalg.norm(estimated - ground_truth, axis=1)
    return {
        "per_frame": per_frame,
        "rmse": float(np.sqrt(np.mean(per_frame**2))),
        "mean": float(np.mean(per_frame)),
        "max": float(np.max(per_frame)),
    }


def relative_pose_error(estimated: np.ndarray, ground_truth: np.ndarray, delta: int = 1) -> dict:
    """Per-step error between estimated and ground-truth displacement vectors (RPE, translation part).

    Compares the estimated motion from frame i to i+delta against the
    ground-truth motion for the same frame pair -- catches systematic
    per-step drift (e.g. a constant scale error) that ATE alone averages
    out over the trajectory. Rotation part not included: none of the
    recorded sequences so far have ground-truth orientation (pure
    translation routes, see docs/daily-log.md, Tag 6/Tag 11) -- see
    rotation_error_deg() for the building block once that data exists.

    Args:
        estimated: (N, 3) VO positions.
        ground_truth: (N, 3) measured (Maßband) positions, same frame/order.
        delta: step size in frames between compared poses (default: 1,
            consecutive frames).

    Returns:
        dict with "per_step" ((N-delta,) array, meters), "rmse", "mean", "max".

    Raises:
        ValueError: estimated and ground_truth have different lengths, or
            fewer than delta+1 frames given.
    """
    estimated = np.asarray(estimated, dtype=np.float64)
    ground_truth = np.asarray(ground_truth, dtype=np.float64)
    _check_matching_length(estimated, ground_truth)
    if len(estimated) <= delta:
        raise ValueError(f"need more than {delta} frames (delta), got {len(estimated)}")

    est_steps = estimated[delta:] - estimated[:-delta]
    gt_steps = ground_truth[delta:] - ground_truth[:-delta]
    per_step = np.linalg.norm(est_steps - gt_steps, axis=1)
    return {
        "per_step": per_step,
        "rmse": float(np.sqrt(np.mean(per_step**2))),
        "mean": float(np.mean(per_step)),
        "max": float(np.max(per_step)),
    }


def rotation_error_deg(R_est: np.ndarray, R_gt: np.ndarray) -> float:
    """Angle (degrees) between two rotation matrices, via the trace formula.

    angle = arccos((trace(R_est^T @ R_gt) - 1) / 2). Building block for a
    future rotation RPE once a sequence with ground-truth orientation exists
    (Tag 12, see CHECKLIST.md) -- not wired into relative_pose_error() yet
    since trajectory.yaml currently only stores positions, not full poses.

    Args:
        R_est, R_gt: 3x3 rotation matrices.

    Returns:
        Angle in degrees, in [0, 180].
    """
    R_est = np.asarray(R_est, dtype=np.float64)
    R_gt = np.asarray(R_gt, dtype=np.float64)
    cos_angle = (np.trace(R_est.T @ R_gt) - 1.0) / 2.0
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # guard against floating-point drift outside [-1, 1]
    return float(np.degrees(np.arccos(cos_angle)))
