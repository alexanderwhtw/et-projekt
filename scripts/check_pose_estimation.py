"""Visueller Sanity-Check: 3D-3D-Pose-Schaetzung (Kabsch-Alignment).

Erzeugt zwei synthetische 3D-Punktwolken (Frame_t-1 / Frame_t) durch eine
bekannte Rotation+Translation, schaetzt die Bewegung mit
estimate_relative_pose() zurueck und stellt drei Punktwolken im 3D-Plot
gegenueber:
  - blau:  Frame_t-1 (Referenz)
  - rot:   Frame_t, unausgerichtet (zeigt die simulierte Kamerabewegung)
  - gruen: Frame_t, mit der GESCHAETZTEN Pose zurueckgerechnet
            (sollte die blauen Punkte eng ueberdecken, wenn die Schaetzung
            stimmt)

Da fuer eine 3D-3D-Transformation keine Bildannotation moeglich ist (anders
als bei features.py/stereo_depth.py/temporal_matching.py), ist dies ein
synthetischer Test mit bekannter Ground-Truth-Bewegung, kein Bild-Overlay.

Nutzung:
    python scripts/check_pose_estimation.py [--output PATH] [--n-points N]
                                             [--yaw-deg D] [--translation X Y Z]
                                             [--noise-m SIGMA]
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

from src.localization.pose_estimation import estimate_relative_pose  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "pose_estimation_demo.png"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-points", type=int, default=30)
    parser.add_argument("--yaw-deg", type=float, default=10.0, help="Simulierte Kamera-Rotation um die Y-Achse")
    parser.add_argument("--translation", type=float, nargs=3, default=[0.05, 0.0, 0.15], metavar=("X", "Y", "Z"))
    parser.add_argument("--noise-m", type=float, default=0.003, help="Gaussisches Rauschen auf den Punkten (Meter)")
    args = parser.parse_args()

    rng = np.random.default_rng(42)
    # Szenenpunkte im Zielarbeitsbereich 0,3-2m (siehe CLAUDE.md)
    xy = rng.uniform(-0.5, 0.5, size=(args.n_points, 2))
    z = rng.uniform(0.3, 2.0, size=(args.n_points, 1))
    points_curr = np.hstack([xy, z])

    true_R, _ = cv2.Rodrigues(np.array([0.0, np.radians(args.yaw_deg), 0.0]))
    true_t = np.array(args.translation)
    noise = rng.normal(scale=args.noise_m, size=points_curr.shape)
    points_prev = (true_R @ points_curr.T).T + true_t + noise

    est_R, est_t = estimate_relative_pose(points_prev, points_curr)
    points_curr_aligned = (est_R @ points_curr.T).T + est_t

    rotation_error_deg = np.degrees(np.arccos(np.clip((np.trace(true_R.T @ est_R) - 1) / 2, -1, 1)))
    translation_error_m = np.linalg.norm(true_t - est_t)
    print(f"Rotationsfehler: {rotation_error_deg:.4f} deg")
    print(f"Translationsfehler: {translation_error_m * 1000:.2f} mm")
    print(f"Mittlerer Alignment-Restfehler: {np.linalg.norm(points_prev - points_curr_aligned, axis=1).mean() * 1000:.2f} mm")

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(*points_prev.T, c="blue", label="Frame t-1 (Referenz)", s=40)
    ax.scatter(*points_curr.T, c="red", label="Frame t (unausgerichtet)", s=40, marker="^")
    ax.scatter(*points_curr_aligned.T, c="green", label="Frame t (geschaetzt zurueckgerechnet)", s=40, marker="x")
    for p_prev, p_aligned in zip(points_prev, points_curr_aligned):
        ax.plot(*zip(p_prev, p_aligned), c="gray", linewidth=0.5, alpha=0.5)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m, Tiefe)")
    ax.set_title(
        f"Pose-Schaetzung: Rotationsfehler {rotation_error_deg:.3f} deg, "
        f"Translationsfehler {translation_error_m * 1000:.2f} mm"
    )
    ax.legend()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    print(f"Plot gespeichert: {args.output}")


if __name__ == "__main__":
    main()
