import cv2
import numpy as np
import pytest

from src.calibration.corners import generate_object_points
from src.calibration.intrinsics import calibrate_intrinsics, compute_per_image_reprojection_errors

PATTERN_SIZE = (6, 7)
SQUARE_SIZE = 0.024  # 24mm, verified board square size, see docs/decisions.md, 2026-09-04
IMAGE_SIZE = (640, 480)  # (width, height), OpenCV convention


def _synthetic_calibration_images(
    true_K: np.ndarray, true_dist: np.ndarray, n_images: int = 10, seed: int = 0
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Project a known checkerboard through a known camera at n_images
    varied poses -- gives exact ground truth to calibrate against."""
    object_points = generate_object_points(PATTERN_SIZE, SQUARE_SIZE)
    rng = np.random.default_rng(seed)

    object_points_list, image_points_list = [], []
    for _ in range(n_images):
        rvec = rng.uniform(-0.4, 0.4, size=3)
        tvec = np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.1, 0.1), rng.uniform(0.6, 1.4)])
        projected, _ = cv2.projectPoints(object_points, rvec, tvec, true_K, true_dist)
        image_points_list.append(projected.reshape(-1, 2).astype(np.float32))
        object_points_list.append(object_points)

    return object_points_list, image_points_list


def test_calibrate_intrinsics_recovers_known_camera_matrix_no_distortion():
    true_K = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    true_dist = np.zeros(5)
    object_points_list, image_points_list = _synthetic_calibration_images(true_K, true_dist)

    K, dist, reprojection_error = calibrate_intrinsics(object_points_list, image_points_list, IMAGE_SIZE)

    np.testing.assert_allclose(K, true_K, atol=0.01)
    np.testing.assert_allclose(dist, [true_dist], atol=1e-4)
    assert reprojection_error < 0.01


def test_calibrate_intrinsics_recovers_known_distortion():
    true_K = np.array([[480.0, 0, 310.0], [0, 480.0, 250.0], [0, 0, 1.0]])
    true_dist = np.array([-0.15, 0.05, 0.001, -0.0005, 0.0])  # k1, k2, p1, p2, k3
    object_points_list, image_points_list = _synthetic_calibration_images(true_K, true_dist)

    K, dist, reprojection_error = calibrate_intrinsics(object_points_list, image_points_list, IMAGE_SIZE)

    np.testing.assert_allclose(K, true_K, atol=0.05)
    np.testing.assert_allclose(dist, [true_dist], atol=1e-3)
    assert reprojection_error < 0.05


def test_calibrate_intrinsics_rejects_mismatched_list_lengths():
    object_points = generate_object_points(PATTERN_SIZE, SQUARE_SIZE)
    with pytest.raises(ValueError):
        calibrate_intrinsics([object_points, object_points], [object_points[:, :2]], IMAGE_SIZE)


def test_compute_per_image_reprojection_errors_near_zero_for_noiseless_data():
    true_K = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    true_dist = np.zeros(5)
    object_points_list, image_points_list = _synthetic_calibration_images(true_K, true_dist)
    K, dist, _ = calibrate_intrinsics(object_points_list, image_points_list, IMAGE_SIZE)

    errors = compute_per_image_reprojection_errors(object_points_list, image_points_list, K, dist)

    assert errors.shape == (len(object_points_list),)
    assert np.all(errors < 0.01)


def test_compute_per_image_reprojection_errors_flags_corrupted_image():
    true_K = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    true_dist = np.zeros(5)
    object_points_list, image_points_list = _synthetic_calibration_images(true_K, true_dist)
    K, dist, _ = calibrate_intrinsics(object_points_list, image_points_list, IMAGE_SIZE)

    # a *uniform* shift of all corners would just be absorbed by solvePnP
    # re-fitting a slightly different pose -> use independent per-corner
    # noise instead, which no single rigid pose can explain away
    corrupted = [pts.copy() for pts in image_points_list]
    rng = np.random.default_rng(1)
    corrupted[3] = (corrupted[3] + rng.uniform(-5.0, 5.0, size=corrupted[3].shape)).astype(np.float32)

    errors = compute_per_image_reprojection_errors(object_points_list, corrupted, K, dist)

    assert errors[3] > 2.0
    other_errors = np.delete(errors, 3)
    assert np.all(other_errors < 0.01)
    assert errors[3] > other_errors.max() * 100
