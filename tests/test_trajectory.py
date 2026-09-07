import cv2
import numpy as np

from src.localization.trajectory import chain_poses, positions_from_poses, to_homogeneous


def test_to_homogeneous_builds_correct_matrix():
    R = np.diag([1.0, -1.0, -1.0])  # arbitrary valid rotation-like matrix for a pure structure test
    t = np.array([1.0, 2.0, 3.0])

    T = to_homogeneous(R, t)

    np.testing.assert_allclose(T[:3, :3], R)
    np.testing.assert_allclose(T[:3, 3], t)
    np.testing.assert_allclose(T[3], [0, 0, 0, 1])


def test_chain_poses_defaults_to_identity_start():
    poses = chain_poses([])
    assert len(poses) == 1
    np.testing.assert_allclose(poses[0], np.eye(4))


def test_chain_poses_pure_translation_accumulates():
    identity = np.eye(3)
    step = np.array([1.0, 0.0, 0.0])
    relative_poses = [(identity, step), (identity, step), (identity, step)]

    poses = chain_poses(relative_poses)
    positions = positions_from_poses(poses)

    np.testing.assert_allclose(positions, [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]])


def test_chain_poses_composes_rotation_and_translation_correctly():
    # step 1: rotate 90 deg around Z, no translation
    # step 2: move 1 unit along the (now rotated) local X axis
    # a naive sum would land at (1,0,0) -- correct chaining lands at (0,1,0)
    R_rot90z, _ = cv2.Rodrigues(np.array([0.0, 0.0, np.pi / 2]))
    relative_poses = [(R_rot90z, np.zeros(3)), (np.eye(3), np.array([1.0, 0.0, 0.0]))]

    poses = chain_poses(relative_poses)

    assert len(poses) == 3
    np.testing.assert_allclose(poses[0], np.eye(4), atol=1e-9)
    np.testing.assert_allclose(poses[2][:3, 3], [0.0, 1.0, 0.0], atol=1e-9)


def test_chain_poses_respects_custom_initial_pose():
    initial_pose = np.eye(4)
    initial_pose[:3, 3] = [10.0, 0.0, 0.0]  # anchored start point, e.g. from reference_points.yaml
    relative_poses = [(np.eye(3), np.array([1.0, 0.0, 0.0]))]

    poses = chain_poses(relative_poses, initial_pose=initial_pose)

    np.testing.assert_allclose(poses[0][:3, 3], [10.0, 0.0, 0.0])
    np.testing.assert_allclose(poses[1][:3, 3], [11.0, 0.0, 0.0])


def test_positions_from_poses_extracts_translation_column():
    poses = [np.eye(4), to_homogeneous(np.eye(3), np.array([1.0, 2.0, 3.0]))]
    positions = positions_from_poses(poses)

    np.testing.assert_allclose(positions, [[0, 0, 0], [1, 2, 3]])
