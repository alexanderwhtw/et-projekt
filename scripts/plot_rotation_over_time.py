"""Rotation ueber Frame-Index: kumulierter Winkel (gegenueber Frame 0) UND
lokaler Schritt-fuer-Schritt-Winkel, in einem Plot.

Hintergrund (siehe docs/decisions.md, 2026-09-21): eine erste Analyse hat
faelschlich die Differenz zweier KUMULIERTER Winkel als lokale Schritt-
Rotation interpretiert -- das ist nur gueltig, wenn die Rotationsachse ueber
die Zeit stabil bleibt, was bei kleinen Winkeln numerisch nicht der Fall ist
(die Achse wird bei fast keiner Drehung rauschdominiert). Der korrekte lokale
Schritt-Winkel ist die Rotation von inv(Pose_t-1) @ Pose_t, nicht die
Differenz zweier unabhaengig berechneter kumulierter Winkel.

Nutzung:
    python scripts/plot_rotation_over_time.py --trajectory PATH \
        [--exclude-frames N N ...] [--output PATH]
"""

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def cumulative_angles_deg(rotations: list[list[list[float]]]) -> np.ndarray:
    """Winkel jeder Pose gegenueber der Startorientierung (Frame 0 = Identitaet)."""
    angles = []
    for R in rotations:
        rvec, _ = cv2.Rodrigues(np.array(R))
        angles.append(np.degrees(np.linalg.norm(rvec)))
    return np.array(angles)


def local_step_angles_deg(rotations: list[list[list[float]]]) -> np.ndarray:
    """Winkel der lokalen Schritt-Rotation inv(R_t-1) @ R_t je Frame-Uebergang."""
    angles = []
    for i in range(1, len(rotations)):
        R_prev, R_curr = np.array(rotations[i - 1]), np.array(rotations[i])
        delta_R = R_prev.T @ R_curr
        rvec, _ = cv2.Rodrigues(delta_R)
        angles.append(np.degrees(np.linalg.norm(rvec)))
    return np.array(angles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument(
        "--exclude-frames", type=int, nargs="*", default=[], metavar="INDEX",
        help="Frame-Indizes, die als Vertikallinien markiert werden (z.B. vom Plausibilitaets-Filter uebersprungene Frames)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Standard: neben der Trajektorie-Datei")
    args = parser.parse_args()

    data = yaml.safe_load(open(args.trajectory))
    rotations = data["rotations"]
    n = len(rotations)

    cumulative = cumulative_angles_deg(rotations)
    local_steps = local_step_angles_deg(rotations)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    axes[0].plot(range(n), cumulative, "-o", markersize=4, color="tab:blue")
    axes[0].set_ylabel("Kumulierter Winkel (deg)\nggü. Frame 0")
    axes[0].set_title(f"Rotation über die Zeit: {args.trajectory.parent.name}")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(range(1, n), local_steps, "-o", markersize=4, color="tab:orange")
    axes[1].set_ylabel("Lokale Schritt-Rotation (deg)\ninv(Pose_t-1)·Pose_t")
    axes[1].set_xlabel("Frame-Index")
    axes[1].grid(True, alpha=0.3)

    for ax in axes:
        for f in args.exclude_frames:
            ax.axvline(f, color="red", linestyle=":", alpha=0.6)
    if args.exclude_frames:
        axes[0].axvline(args.exclude_frames[0], color="red", linestyle=":", alpha=0.6, label="übersprungen (Filter)")
        axes[0].legend(fontsize=8)

    fig.tight_layout()
    output = args.output or args.trajectory.parent / "rotation_over_time.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Plot gespeichert: {output}")


if __name__ == "__main__":
    main()
