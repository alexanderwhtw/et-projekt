import cv2
import numpy as np
import pytest

from src.evaluation.metrics import (
    absolute_trajectory_error,
    relative_pose_error,
    relative_rotation_error,
    rotation_error_deg,
)


def test_ate_zero_for_identical_trajectories():
    positions = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=float)

    result = absolute_trajectory_error(positions, positions)

    np.testing.assert_allclose(result["per_frame"], [0, 0, 0])
    assert result["rmse"] == pytest.approx(0.0)
    assert result["mean"] == pytest.approx(0.0)
    assert result["max"] == pytest.approx(0.0)


def test_ate_known_constant_offset():
    ground_truth = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=float)
    estimated = ground_truth + np.array([0.03, 0.04, 0.0])  # 3-4-5 triangle -> 5cm per frame

    result = absolute_trajectory_error(estimated, ground_truth)

    np.testing.assert_allclose(result["per_frame"], [0.05, 0.05, 0.05])
    assert result["rmse"] == pytest.approx(0.05)
    assert result["mean"] == pytest.approx(0.05)
    assert result["max"] == pytest.approx(0.05)


def test_ate_rejects_length_mismatch():
    with pytest.raises(ValueError):
        absolute_trajectory_error(np.zeros((2, 3)), np.zeros((3, 3)))


def test_rpe_zero_for_matching_step_sizes():
    ground_truth = np.array([[0, 0, 0], [0.2, 0, 0], [0.4, 0, 0], [0.6, 0, 0]], dtype=float)
    # estimated has the same 20cm steps, just globally offset -- RPE looks at
    # step deltas only, so a constant offset must not show up here
    estimated = ground_truth + np.array([1.0, 1.0, 1.0])

    result = relative_pose_error(estimated, ground_truth)

    np.testing.assert_allclose(result["per_step"], [0, 0, 0], atol=1e-9)
    assert result["rmse"] == pytest.approx(0.0)


def test_rpe_detects_systematic_step_scale_error():
    ground_truth = np.array([[0, 0, 0], [0.2, 0, 0], [0.4, 0, 0], [0.6, 0, 0]], dtype=float)
    # VO underestimates each 20cm step by 25% (matches the kind of drift seen
    # in docs/decisions.md, 2026-09-15) -> each step is 5cm short
    estimated = np.array([[0, 0, 0], [0.15, 0, 0], [0.30, 0, 0], [0.45, 0, 0]], dtype=float)

    result = relative_pose_error(estimated, ground_truth)

    np.testing.assert_allclose(result["per_step"], [0.05, 0.05, 0.05], atol=1e-9)
    assert result["rmse"] == pytest.approx(0.05)


def test_rpe_with_delta_greater_than_one_skips_intermediate_frames():
    # delta=2 with 3 frames compares frame 0 directly against frame 2 --
    # an error sitting only on the skipped intermediate frame 1 must not
    # show up
    ground_truth = np.array([[0, 0, 0], [0.2, 0, 0], [0.4, 0, 0]], dtype=float)
    estimated = ground_truth.copy()
    estimated[1] += [0.1, 0, 0]

    result = relative_pose_error(estimated, ground_truth, delta=2)

    np.testing.assert_allclose(result["per_step"], [0], atol=1e-9)


def test_rpe_rejects_length_mismatch():
    with pytest.raises(ValueError):
        relative_pose_error(np.zeros((2, 3)), np.zeros((3, 3)))


def test_rpe_rejects_too_few_frames_for_delta():
    with pytest.raises(ValueError):
        relative_pose_error(np.zeros((2, 3)), np.zeros((2, 3)), delta=2)


def test_rotation_error_zero_for_identical_rotation():
    R, _ = cv2.Rodrigues(np.array([0.1, 0.2, 0.3]))

    assert rotation_error_deg(R, R) == pytest.approx(0.0, abs=1e-3)


def test_rotation_error_known_90_degrees():
    R_gt = np.eye(3)
    R_est, _ = cv2.Rodrigues(np.array([0.0, 0.0, np.radians(90.0)]))  # 90 deg yaw

    assert rotation_error_deg(R_est, R_gt) == pytest.approx(90.0, abs=1e-6)


def test_rotation_error_is_symmetric():
    R_a, _ = cv2.Rodrigues(np.array([0.0, np.radians(10.0), 0.0]))
    R_b, _ = cv2.Rodrigues(np.array([0.0, np.radians(25.0), 0.0]))

    assert rotation_error_deg(R_a, R_b) == pytest.approx(rotation_error_deg(R_b, R_a), abs=1e-9)


def _yaw_sequence(angles_deg: list[float]) -> np.ndarray:
    return np.array([cv2.Rodrigues(np.array([0.0, 0.0, np.radians(a)]))[0] for a in angles_deg])


def test_relative_rotation_error_zero_for_identical_rotations():
    rotations = _yaw_sequence([0.0, 30.0, 60.0])

    result = relative_rotation_error(rotations, rotations)

    np.testing.assert_allclose(result["per_step"], [0, 0], atol=1e-6)
    assert result["rmse"] == pytest.approx(0.0, abs=1e-6)


def test_relative_rotation_error_ignores_constant_absolute_offset():
    # estimated is ground truth rotated by a constant extra 45 deg yaw at
    # every frame -- a global orientation misalignment that must not show up
    # here, since RPE compares relative (frame-to-frame) rotation only, same
    # principle as the translation RPE's constant-offset test above
    ground_truth = _yaw_sequence([0.0, 30.0, 60.0])
    R_offset, _ = cv2.Rodrigues(np.array([0.0, 0.0, np.radians(45.0)]))
    estimated = np.array([R_offset @ R for R in ground_truth])

    result = relative_rotation_error(estimated, ground_truth)

    np.testing.assert_allclose(result["per_step"], [0, 0], atol=1e-6)


def test_relative_rotation_error_detects_known_step_error():
    # ground truth steps 30deg/step, estimated steps 25deg/step -> 5deg
    # per-step rotation error, known-constant case analogous to the
    # translation RPE's systematic-scale-error test above
    ground_truth = _yaw_sequence([0.0, 30.0, 60.0])
    estimated = _yaw_sequence([0.0, 25.0, 50.0])

    result = relative_rotation_error(estimated, ground_truth)

    np.testing.assert_allclose(result["per_step"], [5.0, 5.0], atol=1e-6)
    assert result["rmse"] == pytest.approx(5.0, abs=1e-6)


def test_relative_rotation_error_rejects_length_mismatch():
    with pytest.raises(ValueError):
        relative_rotation_error(np.zeros((2, 3, 3)), np.zeros((3, 3, 3)))


def test_relative_rotation_error_rejects_too_few_frames_for_delta():
    with pytest.raises(ValueError):
        relative_rotation_error(np.zeros((2, 3, 3)), np.zeros((2, 3, 3)), delta=2)
