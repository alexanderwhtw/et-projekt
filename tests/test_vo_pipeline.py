import cv2
import numpy as np
import pytest

from src.localization.vo_pipeline import extract_frame_points, run_vo_pipeline


def _projection_matrices(fx=500.0, fy=500.0, cx=200.0, cy=200.0, baseline=0.06):
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    P_L = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P_R = K @ np.hstack([np.eye(3), np.array([[-baseline], [0], [0]])])
    return P_L, P_R


def _make_scene(size: int = 400, seed: int = 42) -> np.ndarray:
    """Non-repetitive synthetic scene (random circles) -- a checkerboard's
    periodicity causes matching aliasing, see docs/decisions.md, 2026-09-07."""
    rng = np.random.default_rng(seed)
    image = np.full((size, size), 60, dtype=np.uint8)
    for _ in range(40):
        center = tuple(int(v) for v in rng.integers(40, size - 40, size=2))
        radius = int(rng.integers(6, 18))
        color = int(rng.integers(0, 255))
        cv2.circle(image, center, radius, color, thickness=-1)
    return image


def test_extract_frame_points_recovers_known_constant_depth():
    fx, baseline, disparity = 500.0, 0.06, 20
    expected_depth = fx * baseline / disparity
    P_L, P_R = _projection_matrices(fx=fx, fy=fx, baseline=baseline)

    left = _make_scene()
    right = np.roll(left, -disparity, axis=1)

    points_3d, descriptors = extract_frame_points(left, right, P_L, P_R)

    assert points_3d.shape[0] > 50
    assert points_3d.shape == (descriptors.shape[0], 3)
    assert descriptors.shape[1] == 32
    # constant-depth synthetic plane -> triangulated depths should cluster
    # tightly around the known depth (a handful of stereo mismatches are
    # expected and tolerated, see docs/decisions.md, 2026-09-07)
    assert abs(np.median(points_3d[:, 2]) - expected_depth) < 0.05


def test_run_vo_pipeline_recovers_known_lateral_translation():
    fx, baseline, disparity = 500.0, 0.06, 20
    depth = fx * baseline / disparity
    P_L, P_R = _projection_matrices(fx=fx, fy=fx, baseline=baseline)

    shift_px = 15
    expected_tx = shift_px * depth / fx  # image shift <-> lateral translation at constant depth

    left0 = _make_scene()
    right0 = np.roll(left0, -disparity, axis=1)
    left1 = np.roll(left0, -shift_px, axis=1)
    right1 = np.roll(left1, -disparity, axis=1)

    poses = run_vo_pipeline([(left0, right0), (left1, right1)], P_L, P_R, seed=0)

    assert len(poses) == 2
    np.testing.assert_allclose(poses[0], np.eye(4))

    translation = poses[1][:3, 3]
    rotation_angle_deg = np.degrees(np.arccos(np.clip((np.trace(poses[1][:3, :3]) - 1) / 2, -1, 1)))
    assert abs(translation[0] - expected_tx) < 0.01  # 1cm tolerance
    assert abs(translation[1]) < 0.01
    assert abs(translation[2]) < 0.01
    assert rotation_angle_deg < 1.0


def test_run_vo_pipeline_single_frame_returns_only_initial_pose():
    P_L, P_R = _projection_matrices()
    frame = (_make_scene(), np.roll(_make_scene(), -20, axis=1))

    poses = run_vo_pipeline([frame], P_L, P_R)

    assert len(poses) == 1
    np.testing.assert_allclose(poses[0], np.eye(4))


def test_run_vo_pipeline_rejects_empty_input():
    P_L, P_R = _projection_matrices()
    with pytest.raises(ValueError):
        run_vo_pipeline([], P_L, P_R)


def test_run_vo_pipeline_raises_on_unrelated_frames():
    # two completely different random-noise images share no real features
    # -> too few temporal matches to estimate a pose
    P_L, P_R = _projection_matrices()
    rng = np.random.default_rng(0)
    noise_a = rng.integers(0, 255, size=(400, 400), dtype=np.uint8)
    noise_b = rng.integers(0, 255, size=(400, 400), dtype=np.uint8)
    frame_a = (noise_a, np.roll(noise_a, -20, axis=1))
    frame_b = (noise_b, np.roll(noise_b, -20, axis=1))

    with pytest.raises(RuntimeError):
        run_vo_pipeline([frame_a, frame_b], P_L, P_R)
