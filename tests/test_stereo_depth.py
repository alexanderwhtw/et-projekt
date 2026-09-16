import cv2
import numpy as np
import pytest

from src.localization.stereo_depth import compute_disparity_map, match_stereo_pairs, triangulate_matches


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


def _descriptor(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=32, dtype=np.uint8)


def test_match_stereo_pairs_keeps_only_valid_epipolar_matches():
    # pair 0: same row, positive disparity -> valid
    # pair 1: y off by 30px (> max_y_diff) -> rejected
    # pair 2: x_L < x_R (negative disparity) -> rejected
    keypoints_L = [
        cv2.KeyPoint(100, 50, 1),
        cv2.KeyPoint(150, 60, 1),
        cv2.KeyPoint(50, 70, 1),
    ]
    keypoints_R = [
        cv2.KeyPoint(80, 50, 1),
        cv2.KeyPoint(130, 90, 1),
        cv2.KeyPoint(90, 70, 1),
    ]
    descriptors_L = np.stack([_descriptor(0), _descriptor(1), _descriptor(2)])
    descriptors_R = np.stack([_descriptor(0), _descriptor(1), _descriptor(2)])

    matches = match_stereo_pairs(keypoints_L, descriptors_L, keypoints_R, descriptors_R)

    assert len(matches) == 1
    assert matches[0].queryIdx == 0
    assert matches[0].trainIdx == 0


def test_match_stereo_pairs_empty_descriptors():
    empty = np.empty((0, 32), dtype=np.uint8)
    matches = match_stereo_pairs([], empty, [], empty)
    assert matches == []


def _rectified_projection_matrices(
    fx: float = 500.0, fy: float = 500.0, cx: float = 320.0, cy: float = 240.0, baseline: float = 0.06
) -> tuple[np.ndarray, np.ndarray]:
    """Standard rectified stereo projection matrices (baseline in meters,
    matching the real Arducam B0266 baseline of 60mm, see docs/decisions.md)."""
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    P_L = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P_R = K @ np.hstack([np.eye(3), np.array([[-baseline], [0], [0]])])
    return P_L, P_R


def _project(P: np.ndarray, point_3d: np.ndarray) -> tuple[float, float]:
    point_h = P @ np.append(point_3d, 1.0)
    return point_h[0] / point_h[2], point_h[1] / point_h[2]


def test_triangulate_matches_recovers_known_3d_points():
    P_L, P_R = _rectified_projection_matrices()
    # depths within the project's target range of 0.3-2m (see CLAUDE.md)
    true_points = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.2, -0.1, 0.5],
            [-0.3, 0.15, 1.8],
        ]
    )

    keypoints_L = [cv2.KeyPoint(*_project(P_L, p), 1) for p in true_points]
    keypoints_R = [cv2.KeyPoint(*_project(P_R, p), 1) for p in true_points]
    matches = [cv2.DMatch(i, i, 0) for i in range(len(true_points))]

    result = triangulate_matches(keypoints_L, keypoints_R, matches, P_L, P_R)

    assert result.shape == (3, 3)
    np.testing.assert_allclose(result, true_points, atol=1e-6)


def test_triangulate_matches_empty_input():
    P_L, P_R = _rectified_projection_matrices()
    result = triangulate_matches([], [], [], P_L, P_R)
    assert result.shape == (0, 3)


def test_compute_disparity_map_recovers_known_constant_disparity():
    disparity_px = 20
    left = _make_scene()
    right = np.roll(left, -disparity_px, axis=1)  # fronto-parallel plane -> constant disparity everywhere

    disparity = compute_disparity_map(left, right)

    assert disparity.shape == left.shape
    valid = disparity[~np.isnan(disparity)]
    assert valid.size > 0.5 * disparity.size  # most of a textured scene should get a match
    assert abs(np.nanmedian(disparity) - disparity_px) < 1.0


def test_compute_disparity_map_rejects_invalid_num_disparities():
    left = _make_scene()
    with pytest.raises(ValueError):
        compute_disparity_map(left, left, num_disparities=50)  # not a multiple of 16
