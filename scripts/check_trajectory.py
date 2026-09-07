"""Visueller Sanity-Check: Trajektorie aus verketteten Relativbewegungen.

Erzeugt eine synthetische Sequenz von Relativbewegungen (sanfte Kurve: pro
Schritt kleine Rotation + Vorwaertsbewegung, wie eine leicht lenkende
Kamera/Rover-Fahrt), verkettet sie mit chain_poses() und stellt den
Top-Down-Pfad (X-Z-Ebene, Y/Hoehe ignoriert) dar.

Dient als fruehe Vorstufe der in docs/decisions.md (2026-09-07) geplanten
Top-Down-Karte (spaeter in src/evaluation/scripts/plot_trajectory_map.py mit
echten Trajektorien + optionalen Landmarken-Punkten) -- hier rein zur
Pruefung, dass die Posen-Verkettung selbst geometrisch sinnvolle Pfade
erzeugt (kein Bild-Overlay moeglich, siehe check_pose_estimation.py).

Nutzung:
    python scripts/check_trajectory.py [--output PATH] [--n-steps N]
                                        [--step-m D] [--yaw-deg-per-step D]
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

from src.localization.trajectory import chain_poses, positions_from_poses  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "trajectory_demo.png"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-steps", type=int, default=20)
    parser.add_argument("--step-m", type=float, default=0.2, help="Vorwaertsbewegung pro Schritt (m)")
    parser.add_argument("--yaw-deg-per-step", type=float, default=4.0, help="Rotation um Y pro Schritt (deg)")
    args = parser.parse_args()

    R_step, _ = cv2.Rodrigues(np.array([0.0, np.radians(args.yaw_deg_per_step), 0.0]))
    t_step = np.array([0.0, 0.0, args.step_m])
    relative_poses = [(R_step, t_step) for _ in range(args.n_steps)]

    poses = chain_poses(relative_poses)
    positions = positions_from_poses(poses)

    path_length = np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()
    displacement = np.linalg.norm(positions[-1] - positions[0])
    print(f"{len(poses)} Posen, Pfadlaenge {path_length:.2f}m, direkte Distanz Start->Ende {displacement:.2f}m")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(positions[:, 0], positions[:, 2], "-o", color="tab:blue", markersize=4)
    ax.scatter(*positions[0, [0, 2]], c="green", s=100, marker="*", zorder=5, label="Start")
    ax.scatter(*positions[-1, [0, 2]], c="red", s=100, marker="X", zorder=5, label="Ende")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_title(f"Top-Down-Trajektorie ({args.n_steps} Schritte, {args.yaw_deg_per_step} deg/Schritt)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    print(f"Plot gespeichert: {args.output}")


if __name__ == "__main__":
    main()
