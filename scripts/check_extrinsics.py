"""Visueller Sanity-Check: Stereo-Rig-Geometrie aus der Extrinsic-Kalibrierung.

Zeigt in 3D: die linke Kamera (Referenz-Ursprung), die rechte Kamera an der
geschaetzten Position/Orientierung (R, T), und die Schachbrett-Posen, die
fuer die Kalibrierung genutzt wurden -- macht sowohl die Baseline/Verkippung
als auch die Posen-Abdeckung (wichtig fuer eine gute Kalibrierung) auf einen
Blick sichtbar.

Nutzung:
    python scripts/check_extrinsics.py [--output PATH] [--n-poses N]

Nutzt ein synthetisches Stereo-Set mit bekannter Geometrie (echte Baseline
60mm, siehe docs/decisions.md) -- echte Kalibrierbilder liegen noch nicht
vor (Phase 1 Datenaufnahme steht aus).
"""

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.corners import generate_object_points  # noqa: E402
from src.calibration.extrinsics import calibrate_extrinsics  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "extrinsics_demo.png"
PATTERN_SIZE = (6, 7)
SQUARE_SIZE = 0.024
BASELINE = 0.06  # reale Arducam B0266 Baseline, siehe docs/decisions.md, 2026-09-02


def _make_synthetic_stereo_set(n_poses: int, seed: int = 0):
    K_L = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    K_R = np.array([[505.0, 0, 315.0], [0, 505.0, 245.0], [0, 0, 1.0]])
    dist = np.zeros(5)
    true_R = cv2.Rodrigues(np.array([0.0, np.radians(1.0), 0.0]))[0]
    true_T = np.array([BASELINE, 0.0, 0.0])

    object_points = generate_object_points(PATTERN_SIZE, SQUARE_SIZE)
    rvec_extrinsic = cv2.Rodrigues(true_R)[0].flatten()
    rng = np.random.default_rng(seed)

    object_points_list, image_points_L_list, image_points_R_list, board_poses = [], [], [], []
    for _ in range(n_poses):
        rvec_L = rng.uniform(-0.4, 0.4, size=3)
        tvec_L = np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.1, 0.1), rng.uniform(0.6, 1.4)])
        rvec_R, tvec_R = cv2.composeRT(rvec_L, tvec_L, rvec_extrinsic, true_T)[:2]

        proj_L, _ = cv2.projectPoints(object_points, rvec_L, tvec_L, K_L, dist)
        proj_R, _ = cv2.projectPoints(object_points, rvec_R, tvec_R, K_R, dist)

        object_points_list.append(object_points)
        image_points_L_list.append(proj_L.reshape(-1, 2).astype(np.float32))
        image_points_R_list.append(proj_R.reshape(-1, 2).astype(np.float32))
        board_poses.append((rvec_L, tvec_L))

    return K_L, K_R, dist, dist, object_points_list, image_points_L_list, image_points_R_list, board_poses


def _draw_camera(ax, center, R_ref_from_cam, color, label, axis_length=0.03):
    ax.scatter(*center, c=color, s=60, marker="s", label=label)
    axis_names = ["X", "Y", "Z"]
    for i, axis_color in enumerate(["red", "green", "blue"]):
        tip = center + R_ref_from_cam[:, i] * axis_length
        ax.plot(*zip(center, tip), c=axis_color, linewidth=2)


def _board_corners_in_ref_frame(rvec, tvec, pattern_size, square_size):
    cols, rows = pattern_size
    local_corners = np.array(
        [[0, 0, 0], [(cols - 1) * square_size, 0, 0], [(cols - 1) * square_size, (rows - 1) * square_size, 0], [0, (rows - 1) * square_size, 0]]
    )
    R, _ = cv2.Rodrigues(rvec)
    return (R @ local_corners.T).T + tvec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-poses", type=int, default=8)
    args = parser.parse_args()

    K_L, K_R, dist_L, dist_R, object_points_list, image_points_L_list, image_points_R_list, board_poses = (
        _make_synthetic_stereo_set(args.n_poses)
    )
    image_size = (640, 480)

    R, T, reprojection_error = calibrate_extrinsics(
        object_points_list, image_points_L_list, image_points_R_list, K_L, dist_L, K_R, dist_R, image_size
    )
    baseline = np.linalg.norm(T)
    print(f"Baseline: {baseline * 1000:.2f}mm (real gemessen: {BASELINE * 1000:.0f}mm, siehe docs/decisions.md)")
    print(f"Reprojection Error: {reprojection_error:.4f}px")

    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")

    _draw_camera(ax, np.zeros(3), np.eye(3), "tab:blue", "Linke Kamera (Referenz)")
    right_center = -R.T @ T
    _draw_camera(ax, right_center, R.T, "tab:orange", "Rechte Kamera (geschaetzt)")

    cmap = plt.get_cmap("viridis")
    for i, (rvec, tvec) in enumerate(board_poses):
        corners = _board_corners_in_ref_frame(rvec, tvec, PATTERN_SIZE, SQUARE_SIZE)
        loop = np.vstack([corners, corners[0]])
        ax.plot(loop[:, 0], loop[:, 1], loop[:, 2], color=cmap(i / max(len(board_poses) - 1, 1)), alpha=0.7)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title(f"Stereo-Rig-Geometrie: Baseline {baseline * 1000:.1f}mm, {len(board_poses)} Kalibrierposen")
    ax.legend()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    print(f"Plot gespeichert: {args.output}")


if __name__ == "__main__":
    main()
