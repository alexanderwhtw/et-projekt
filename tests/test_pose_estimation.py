import cv2
import numpy as np
import pytest

from src.localization.pose_estimation import estimate_relative_pose, estimate_relative_pose_ransac


def _random_points(n: int = 20, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # plausible scene points relative to the camera: within the project's
    # target depth range of 0.3-2m (see CLAUDE.md), moderate lateral spread
    xy = rng.uniform(-0.5, 0.5, size=(n, 2))
    z = rng.uniform(0.3, 2.0, size=(n, 1))
    return np.hstack([xy, z])


def test_estimate_relative_pose_identity_transform():
    points = _random_points()
    R, t = estimate_relative_pose(points, points)

    np.testing.assert_allclose(R, np.eye(3), atol=1e-9)
    np.testing.assert_allclose(t, np.zeros(3), atol=1e-9)


def test_estimate_relative_pose_pure_translation():
    points_curr = _random_points()
    true_t = np.array([0.1, -0.05, 0.2])
    points_prev = points_curr + true_t

    R, t = estimate_relative_pose(points_prev, points_curr)

    np.testing.assert_allclose(R, np.eye(3), atol=1e-9)
    np.testing.assert_allclose(t, true_t, atol=1e-9)


def test_estimate_relative_pose_recovers_known_rotation_and_translation():
    points_curr = _random_points()
    true_R, _ = cv2.Rodrigues(np.array([0.0, np.radians(10.0), 0.0]))  # 10 deg yaw
    true_t = np.array([0.05, 0.0, 0.15])
    points_prev = (true_R @ points_curr.T).T + true_t

    R, t = estimate_relative_pose(points_prev, points_curr)

    np.testing.assert_allclose(R, true_R, atol=1e-9)
    np.testing.assert_allclose(t, true_t, atol=1e-9)


def test_estimate_relative_pose_robust_to_small_noise():
    points_curr = _random_points(n=30)
    true_R, _ = cv2.Rodrigues(np.array([0.0, np.radians(5.0), 0.0]))
    true_t = np.array([0.02, 0.01, 0.1])
    rng = np.random.default_rng(1)
    noise = rng.normal(scale=0.003, size=points_curr.shape)  # 3mm, sub-pixel-triangulation-level noise
    points_prev = (true_R @ points_curr.T).T + true_t + noise

    R, t = estimate_relative_pose(points_prev, points_curr)

    np.testing.assert_allclose(R, true_R, atol=0.01)
    np.testing.assert_allclose(t, true_t, atol=0.01)


def test_estimate_relative_pose_rejects_too_few_points():
    points = _random_points(n=2)
    with pytest.raises(ValueError):
        estimate_relative_pose(points, points)


def test_ransac_matches_plain_kabsch_when_no_outliers():
    points_curr = _random_points(n=20)
    true_R, _ = cv2.Rodrigues(np.array([0.0, np.radians(8.0), 0.0]))
    true_t = np.array([0.03, -0.01, 0.1])
    points_prev = (true_R @ points_curr.T).T + true_t

    R, t, inlier_mask = estimate_relative_pose_ransac(points_prev, points_curr, inlier_threshold=0.02, seed=0)

    np.testing.assert_allclose(R, true_R, atol=1e-6)
    np.testing.assert_allclose(t, true_t, atol=1e-6)
    assert inlier_mask.all()


def test_ransac_recovers_pose_despite_outliers():
    # matches the real finding while building vo_pipeline.py: ~39% of
    # temporal correspondences can be outliers (see docs/decisions.md,
    # 2026-09-07) -- construct a comparable scenario and verify RANSAC still
    # recovers the true motion and correctly flags the corrupted points.
    points_curr = _random_points(n=30)
    true_R, _ = cv2.Rodrigues(np.array([0.0, np.radians(6.0), 0.0]))
    true_t = np.array([0.04, 0.0, 0.08])
    points_prev = (true_R @ points_curr.T).T + true_t

    rng = np.random.default_rng(2)
    n_outliers = 12  # 40%
    outlier_idx = rng.choice(len(points_prev), size=n_outliers, replace=False)
    points_prev[outlier_idx] += rng.uniform(-0.3, 0.3, size=(n_outliers, 3))

    R, t, inlier_mask = estimate_relative_pose_ransac(points_prev, points_curr, inlier_threshold=0.02, seed=0)

    np.testing.assert_allclose(R, true_R, atol=1e-6)
    np.testing.assert_allclose(t, true_t, atol=1e-6)
    expected_inliers = np.ones(len(points_prev), dtype=bool)
    expected_inliers[outlier_idx] = False
    np.testing.assert_array_equal(inlier_mask, expected_inliers)


def test_ransac_rejects_too_few_points():
    points = _random_points(n=2)
    with pytest.raises(ValueError):
        estimate_relative_pose_ransac(points, points)


def test_ransac_rejects_degenerate_inlier_set():
    # 3 points is the minimum RANSAC can sample; a 3-point Kabsch fit is
    # only exact for noiseless, perfectly consistent correspondences --
    # real triangulated points carry noise, so an unrelated/inconsistent
    # 3-point correspondence under a tight threshold can end up with fewer
    # than 3 inliers even for its own fitted points. Reproduces a live
    # crash seen on 2026-09-17 (noisier images from reduced exposure +
    # higher gain, see docs/decisions.md) -- previously an uncaught
    # ValueError instead of a catchable RuntimeError.
    rng = np.random.default_rng(0)
    points_prev = rng.uniform(-1, 1, size=(3, 3))
    points_curr = rng.uniform(-1, 1, size=(3, 3))  # unrelated -- no rigid transform fits all 3

    with pytest.raises(RuntimeError):
        estimate_relative_pose_ransac(points_prev, points_curr, inlier_threshold=1e-9, seed=0)
