"""Chain relative camera motions into an absolute trajectory.

Pure logic: operates on (R, t) pairs from pose_estimation.estimate_relative_pose()
and a starting pose (the vermessene Startpunkt-Verankerung, see
data/reference_points.yaml). No file I/O -- loading the start point from YAML
is a separate, later concern.

Pose_t = Pose_t-1 . Delta-Pose_t (see docs/decisions.md, 2026-09-04): no
loop-closure, no global correction, small per-step errors accumulate
unchecked over the trajectory (drift), by design (see CLAUDE.md).
"""

from typing import Sequence

import numpy as np


def to_homogeneous(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Build a 4x4 homogeneous transform from a rotation matrix and translation."""
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def chain_poses(
    relative_poses: Sequence[tuple[np.ndarray, np.ndarray]],
    initial_pose: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Chain relative (R, t) motions into a trajectory of absolute poses.

    Args:
        relative_poses: (R, t) pairs from estimate_relative_pose(), one per
            consecutive frame pair, in temporal order.
        initial_pose: 4x4 homogeneous pose of the first frame (world <-
            camera_0). Defaults to the identity (origin) if not given.

    Returns:
        List of len(relative_poses) + 1 4x4 absolute poses (world <-
        camera_i), starting with initial_pose.
    """
    pose_0 = np.eye(4) if initial_pose is None else np.asarray(initial_pose, dtype=np.float64)

    poses = [pose_0]
    for R, t in relative_poses:
        poses.append(poses[-1] @ to_homogeneous(R, t))
    return poses


def positions_from_poses(poses: Sequence[np.ndarray]) -> np.ndarray:
    """Extract the (N, 3) camera positions (translation part) from absolute poses."""
    return np.array([pose[:3, 3] for pose in poses])
