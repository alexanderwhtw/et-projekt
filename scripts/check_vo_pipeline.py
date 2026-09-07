"""Visueller Sanity-Check: die komplette VO-Kette (Bilder -> Trajektorie).

Anders als check_trajectory.py (das direkt Relativbewegungen vorgibt) laeuft
hier eine synthetische Bildsequenz durch die GESAMTE Pipeline
(detect_features -> match_stereo_pairs -> triangulate_matches ->
match_temporal_features -> estimate_relative_pose_ransac -> chain_poses,
via run_vo_pipeline()) -- der Beleg, dass alle Bausteine zusammen
funktionieren, bevor echte Kalibrier-/Kamerad daten verfuegbar sind.

Die Szene ist eine fronto-parallele Ebene mit bekannter Tiefe, die Kamera
bewegt sich in bekannten, gleichmaessigen seitlichen Schritten -> die
geschaetzte Top-Down-Trajektorie sollte einer geraden Linie mit bekannter
Schrittweite folgen (Ground-Truth-Linie zum Vergleich eingezeichnet).

Nutzung:
    python scripts/check_vo_pipeline.py [--output PATH] [--n-frames N]
                                         [--step-px PX] [--disparity-px PX]
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

from src.localization.trajectory import positions_from_poses  # noqa: E402
from src.localization.vo_pipeline import run_vo_pipeline  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "vo_pipeline_demo.png"


def _make_scene(size: int = 400, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = np.full((size, size), 60, dtype=np.uint8)
    for _ in range(40):
        center = tuple(int(v) for v in rng.integers(40, size - 40, size=2))
        radius = int(rng.integers(6, 18))
        color = int(rng.integers(0, 255))
        cv2.circle(image, center, radius, color, thickness=-1)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-frames", type=int, default=8)
    parser.add_argument("--step-px", type=int, default=15, help="Bildverschiebung pro Schritt (simulierte seitliche Bewegung)")
    parser.add_argument("--disparity-px", type=int, default=20, help="Stereo-Disparitaet der synthetischen Szene")
    args = parser.parse_args()

    fx = fy = 500.0
    cx = cy = 200.0
    baseline = 0.06  # reale Baseline des Arducam B0266, siehe docs/decisions.md
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    P_L = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P_R = K @ np.hstack([np.eye(3), np.array([[-baseline], [0], [0]])])

    depth = fx * baseline / args.disparity_px
    expected_step_m = args.step_px * depth / fx
    print(f"Simulierte Tiefe: {depth:.2f}m, erwarteter Schritt: {expected_step_m * 1000:.1f}mm")

    base_scene = _make_scene()
    stereo_frames = []
    for i in range(args.n_frames):
        left = np.roll(base_scene, -i * args.step_px, axis=1)
        right = np.roll(left, -args.disparity_px, axis=1)
        stereo_frames.append((left, right))

    poses = run_vo_pipeline(stereo_frames, P_L, P_R, seed=0)
    positions = positions_from_poses(poses)

    print(f"{len(poses)} Posen geschaetzt.")
    for i, pos in enumerate(positions):
        print(f"  Frame {i}: x={pos[0] * 1000:.1f}mm  y={pos[1] * 1000:.1f}mm  z={pos[2] * 1000:.1f}mm")

    expected_x = np.arange(args.n_frames) * expected_step_m

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(expected_x, np.zeros_like(expected_x), "--", color="gray", label="Ground Truth (bekannte Verschiebung)")
    ax.plot(positions[:, 0], positions[:, 2], "-o", color="tab:blue", label="VO-Pipeline (geschaetzt)")
    ax.scatter(*positions[0, [0, 2]], c="green", s=100, marker="*", zorder=5, label="Start")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_title("VO-Pipeline End-to-End (synthetische Bildsequenz)")
    ax.grid(True, alpha=0.3)
    ax.legend()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    print(f"Plot gespeichert: {args.output}")


if __name__ == "__main__":
    main()
