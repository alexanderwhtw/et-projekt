import cv2
import numpy as np

from src.calibration.rectification import compute_rectification, compute_rectification_maps

IMAGE_SIZE = (640, 480)
BASELINE = 0.06  # 60mm, measured Arducam B0266 baseline, see docs/decisions.md, 2026-09-02


def _synthetic_stereo_rig():
    K_L = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    K_R = np.array([[505.0, 0, 315.0], [0, 505.0, 245.0], [0, 0, 1.0]])
    dist_L = np.array([-0.1, 0.02, 0, 0, 0])
    dist_R = np.array([-0.08, 0.01, 0, 0, 0])
    # comparable to the current prototype's un-rectified roll misalignment
    # (~2.25 deg, see docs/decisions.md, 2026-09-02)
    R = cv2.Rodrigues(np.array([0.0, np.radians(1.0), np.radians(2.25)]))[0]
    T = np.array([BASELINE, 0.001, -0.0005])
    return K_L, dist_L, K_R, dist_R, R, T


def test_compute_rectification_produces_valid_rotations():
    K_L, dist_L, K_R, dist_R, R, T = _synthetic_stereo_rig()

    R1, R2, P1, P2, Q = compute_rectification(K_L, dist_L, K_R, dist_R, IMAGE_SIZE, R, T)

    for rectifying_rotation in (R1, R2):
        np.testing.assert_allclose(rectifying_rotation @ rectifying_rotation.T, np.eye(3), atol=1e-9)
        assert abs(np.linalg.det(rectifying_rotation) - 1.0) < 1e-9
    assert P1.shape == (3, 4)
    assert P2.shape == (3, 4)
    assert Q.shape == (4, 4)


def test_compute_rectification_recovers_known_baseline():
    K_L, dist_L, K_R, dist_R, R, T = _synthetic_stereo_rig()

    _R1, _R2, P1, P2, _Q = compute_rectification(K_L, dist_L, K_R, dist_R, IMAGE_SIZE, R, T)

    np.testing.assert_allclose(P1[:, 3], 0.0, atol=1e-9)  # left camera is the rectified reference
    recovered_baseline = abs(P2[0, 3] / P2[0, 0])
    assert abs(recovered_baseline - np.linalg.norm(T)) < 1e-9


def test_compute_rectification_makes_epipolar_lines_horizontal():
    # the whole point of rectification: for a 3D point expressed in the
    # ORIGINAL left-camera frame, P1/P2 must project it to the same image
    # row (see localization.stereo_depth.match_stereo_pairs(), which
    # assumes exactly this on its rectified input)
    K_L, dist_L, K_R, dist_R, R, T = _synthetic_stereo_rig()
    _R1, _R2, P1, P2, _Q = compute_rectification(K_L, dist_L, K_R, dist_R, IMAGE_SIZE, R, T)

    points_3d_homogeneous = np.array(
        [
            [0.05, -0.03, 1.2, 1.0],
            [-0.1, 0.08, 0.5, 1.0],
            [0.0, 0.0, 2.0, 1.0],
        ]
    )

    for point in points_3d_homogeneous:
        x1 = P1 @ point
        x2 = P2 @ point
        y1, y2 = x1[1] / x1[2], x2[1] / x2[2]
        assert abs(y1 - y2) < 1e-9


def test_compute_rectification_maps_have_correct_shape():
    K_L, dist_L, K_R, dist_R, R, T = _synthetic_stereo_rig()
    R1, _R2, P1, _P2, _Q = compute_rectification(K_L, dist_L, K_R, dist_R, IMAGE_SIZE, R, T)

    map_x, map_y = compute_rectification_maps(K_L, dist_L, R1, P1, IMAGE_SIZE)

    width, height = IMAGE_SIZE
    assert map_x.shape == (height, width)
    assert map_y.shape == (height, width)
    assert np.isfinite(map_x).all()
    assert np.isfinite(map_y).all()
