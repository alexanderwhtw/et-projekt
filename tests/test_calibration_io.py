import csv

import cv2
import numpy as np
import pytest

from src.calibration.io import load_calibration_manifest, load_calibration_result, save_calibration_result


def _write_manifest_and_images(directory, rows):
    manifest_path = directory / "manifest.csv"
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "distanz_m", "notiz", "shutter", "gain", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)

    dummy_image = np.zeros((10, 10), dtype=np.uint8)
    for row in rows:
        index = int(row["index"])
        cv2.imwrite(str(directory / f"left_{index:03d}.png"), dummy_image)
        cv2.imwrite(str(directory / f"right_{index:03d}.png"), dummy_image)


def test_load_calibration_manifest_parses_rows_and_resolves_paths(tmp_path):
    rows = [
        {"index": 0, "distanz_m": 1.0, "notiz": "frontal", "shutter": 10000, "gain": 1.0, "timestamp": "t0"},
        {"index": 1, "distanz_m": 1.5, "notiz": "gekippt", "shutter": 10000, "gain": 1.0, "timestamp": "t1"},
    ]
    _write_manifest_and_images(tmp_path, rows)

    entries = load_calibration_manifest(tmp_path)

    assert len(entries) == 2
    assert entries[0]["notiz"] == "frontal"
    assert entries[0]["left_path"] == tmp_path / "left_000.png"
    assert entries[0]["right_path"] == tmp_path / "right_000.png"
    assert entries[1]["left_path"].is_file()


def test_load_calibration_manifest_missing_manifest_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_calibration_manifest(tmp_path)


def test_load_calibration_manifest_missing_image_raises(tmp_path):
    rows = [{"index": 0, "distanz_m": 1.0, "notiz": "", "shutter": 10000, "gain": 1.0, "timestamp": "t0"}]
    _write_manifest_and_images(tmp_path, rows)
    (tmp_path / "right_000.png").unlink()

    with pytest.raises(FileNotFoundError):
        load_calibration_manifest(tmp_path)


def test_save_and_load_calibration_result_round_trip(tmp_path):
    K_L = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    dist_L = np.array([[-0.1, 0.02, 0.0, 0.0, 0.0]])
    K_R = np.array([[505.0, 0, 315.0], [0, 505.0, 245.0], [0, 0, 1.0]])
    dist_R = np.array([[-0.08, 0.01, 0.0, 0.0, 0.0]])
    R = cv2.Rodrigues(np.array([0.0, np.radians(1.0), np.radians(2.25)]))[0]
    T = np.array([0.06, 0.001, -0.0005])
    R1, R2 = np.eye(3), np.eye(3)
    P1 = np.hstack([K_L, np.zeros((3, 1))])
    P2 = np.hstack([K_R, np.array([[-30.0], [0.0], [0.0]])])
    Q = np.eye(4)

    path = tmp_path / "2026-09-07_calibration.yaml"
    save_calibration_result(
        path,
        date="2026-09-07",
        image_size=(640, 480),
        K_L=K_L, dist_L=dist_L, error_L=0.42,
        K_R=K_R, dist_R=dist_R, error_R=0.39,
        R=R, T=T, error_stereo=0.51,
        R1=R1, R2=R2, P1=P1, P2=P2, Q=Q,
    )
    result = load_calibration_result(path)

    assert result["date"] == "2026-09-07"
    assert result["image_size"] == (640, 480)
    np.testing.assert_allclose(result["left"]["K"], K_L)
    np.testing.assert_allclose(result["left"]["dist"], dist_L)
    assert result["left"]["reprojection_error_px"] == pytest.approx(0.42)
    np.testing.assert_allclose(result["stereo"]["R"], R)
    np.testing.assert_allclose(result["stereo"]["T"], T)
    assert result["stereo"]["baseline_m"] == pytest.approx(np.linalg.norm(T))
    np.testing.assert_allclose(result["rectification"]["P1"], P1)
    np.testing.assert_allclose(result["rectification"]["P2"], P2)
    np.testing.assert_allclose(result["rectification"]["Q"], Q)
