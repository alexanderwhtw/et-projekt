import cv2
import numpy as np

from src.calibration.corners import generate_object_points
from src.calibration.extrinsics import calibrate_extrinsics

PATTERN_SIZE = (6, 7)
SQUARE_SIZE = 0.024  # 24mm, verified board square size, see docs/decisions.md, 2026-09-04
IMAGE_SIZE = (640, 480)
BASELINE = 0.06  # 60mm, measured Arducam B0266 baseline, see docs/decisions.md, 2026-09-02


def _synthetic_stereo_calibration_set(
    K_L: np.ndarray,
    dist_L: np.ndarray,
    K_R: np.ndarray,
    dist_R: np.ndarray,
    true_R: np.ndarray,
    true_T: np.ndarray,
    n_pairs: int = 10,
    seed: int = 0,
) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]:
    """Project a known checkerboard, at varied poses relative to the left
    camera, through both cameras of a known stereo rig -- exact ground
    truth to calibrate the extrinsics against."""
    object_points = generate_object_points(PATTERN_SIZE, SQUARE_SIZE)
    rvec_extrinsic = cv2.Rodrigues(true_R)[0].flatten()
    rng = np.random.default_rng(seed)

    object_points_list, image_points_L_list, image_points_R_list = [], [], []
    for _ in range(n_pairs):
        rvec_L = rng.uniform(-0.4, 0.4, size=3)
        tvec_L = np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.1, 0.1), rng.uniform(0.6, 1.4)])
        rvec_R, tvec_R = cv2.composeRT(rvec_L, tvec_L, rvec_extrinsic, true_T)[:2]

        proj_L, _ = cv2.projectPoints(object_points, rvec_L, tvec_L, K_L, dist_L)
        proj_R, _ = cv2.projectPoints(object_points, rvec_R, tvec_R, K_R, dist_R)

        object_points_list.append(object_points)
        image_points_L_list.append(proj_L.reshape(-1, 2).astype(np.float32))
        image_points_R_list.append(proj_R.reshape(-1, 2).astype(np.float32))

    return object_points_list, image_points_L_list, image_points_R_list


def test_calibrate_extrinsics_recovers_known_baseline_and_rotation():
    K_L = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    K_R = np.array([[505.0, 0, 315.0], [0, 505.0, 245.0], [0, 0, 1.0]])
    dist_L = dist_R = np.zeros(5)
    # slight real-world misalignment, comparable to the measured ~2.25 deg
    # roll from the un-rectified rig, see docs/decisions.md, 2026-09-02
    true_R = cv2.Rodrigues(np.array([0.0, np.radians(1.0), 0.0]))[0]
    true_T = np.array([BASELINE, 0.0, 0.0])

    object_points_list, image_points_L_list, image_points_R_list = _synthetic_stereo_calibration_set(
        K_L, dist_L, K_R, dist_R, true_R, true_T
    )

    R, T, reprojection_error = calibrate_extrinsics(
        object_points_list, image_points_L_list, image_points_R_list, K_L, dist_L, K_R, dist_R, IMAGE_SIZE
    )

    np.testing.assert_allclose(R, true_R, atol=1e-4)
    np.testing.assert_allclose(T, true_T, atol=1e-4)
    assert abs(np.linalg.norm(T) - BASELINE) < 1e-4
    assert reprojection_error < 0.01


def test_calibrate_extrinsics_identity_when_cameras_aligned():
    K_L = K_R = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    dist_L = dist_R = np.zeros(5)
    true_R = np.eye(3)
    true_T = np.array([BASELINE, 0.0, 0.0])

    object_points_list, image_points_L_list, image_points_R_list = _synthetic_stereo_calibration_set(
        K_L, dist_L, K_R, dist_R, true_R, true_T
    )

    R, T, _ = calibrate_extrinsics(
        object_points_list, image_points_L_list, image_points_R_list, K_L, dist_L, K_R, dist_R, IMAGE_SIZE
    )

    np.testing.assert_allclose(R, np.eye(3), atol=1e-4)
    np.testing.assert_allclose(T, true_T, atol=1e-4)
