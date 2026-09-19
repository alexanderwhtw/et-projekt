"""Plottet ATE/RPE (Translation + Rotation) ueber die zurueckgelegte Strecke
statt nur als Zahlen auszugeben (siehe scripts/evaluate_trajectory.py).

Zeigt, OB und WIE der Fehler mit der Distanz waechst -- die zentrale
Kernaussage der Drift-Diskussion (kein Loop-Closure, siehe CLAUDE.md).
Distanz (nicht Frame-Index) als X-Achse, weil Schrittweiten zwischen
Sequenzen/Segmenten unterschiedlich sein koennen (z.B. Translations- vs.
Rotationsabschnitte einer verketteten Route, siehe CHECKLIST.md,
Phase-3-Planung).

Rein nachgelagerter Auswertungs-/Visualisierungs-Output auf Basis bereits
berechneter VO-Ergebnisse -- kein Bestandteil des Lokalisierungsalgorithmus,
analog zu plot_trajectory_map.py.

Nutzung:
    python scripts/plot_error_growth.py \
        --trajectory results/measurements/2026-09-08_vo_sequence_test/trajectory.yaml \
        [--reference-points PATH]  # Default: <sequence-dir aus trajectory.yaml>/ground_truth.yaml
        [--rpe-delta N]            # Default: 1 (aufeinanderfolgende Frames)
        [--output PATH]            # Default: neben der Trajektorie-Datei
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.metrics import (  # noqa: E402
    absolute_trajectory_error,
    cumulative_path_length,
    relative_pose_error,
    relative_rotation_error,
)


def load_trajectory_data(trajectory_path: Path) -> dict:
    with open(trajectory_path) as f:
        return yaml.safe_load(f)


def load_positions(trajectory_data: dict) -> np.ndarray:
    return np.array(trajectory_data["positions"], dtype=float)


def load_reference_positions(reference_points_path: Path) -> np.ndarray | None:
    if not reference_points_path.exists():
        return None
    with open(reference_points_path) as f:
        data = yaml.safe_load(f)
    points = list(data.get("points", {}).values())
    return np.array(points, dtype=float) if points else None


def load_reference_rotations_deg(reference_points_path: Path) -> np.ndarray | None:
    if not reference_points_path.exists():
        return None
    with open(reference_points_path) as f:
        data = yaml.safe_load(f)
    rotations_deg = data.get("rotations_deg")
    return np.array(list(rotations_deg.values()), dtype=float) if rotations_deg else None


def rotation_deg_to_matrix(angle_deg: float) -> np.ndarray:
    """Ground-truth yaw angle -> rotation matrix, camera y-axis, negative direction
    (empirically determined axis convention, see docs/decisions.md, 2026-09-17)."""
    R, _ = cv2.Rodrigues(np.array([0.0, -np.radians(angle_deg), 0.0]))
    return R


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument(
        "--reference-points",
        type=Path,
        default=None,
        help="Default: <sequence-dir aus trajectory.yaml>/ground_truth.yaml",
    )
    parser.add_argument("--rpe-delta", type=int, default=1, help="Frame-Abstand fuer RPE (Default: 1)")
    parser.add_argument("--output", type=Path, default=None, help="Standard: neben der Trajektorie-Datei")
    args = parser.parse_args()

    trajectory_data = load_trajectory_data(args.trajectory)
    positions = load_positions(trajectory_data)

    if args.reference_points is not None:
        reference_points_path = args.reference_points
    else:
        sequence_dir = trajectory_data.get("sequence_dir")
        if sequence_dir is None:
            raise ValueError("trajectory.yaml hat kein 'sequence_dir' -- --reference-points explizit angeben")
        reference_points_path = Path(sequence_dir) / "ground_truth.yaml"

    ground_truth = load_reference_positions(reference_points_path)
    if ground_truth is None:
        raise FileNotFoundError(f"Ground-Truth nicht gefunden: {reference_points_path}")
    if len(ground_truth) != len(positions):
        raise ValueError(
            f"{len(ground_truth)} Ground-Truth-Punkte != {len(positions)} Trajektorien-Frames "
            f"({reference_points_path} vs. {args.trajectory})"
        )

    distance = cumulative_path_length(ground_truth)
    ate = absolute_trajectory_error(positions, ground_truth)
    rpe = relative_pose_error(positions, ground_truth, delta=args.rpe_delta)

    ground_truth_rotations_deg = load_reference_rotations_deg(reference_points_path)
    rotations = trajectory_data.get("rotations")
    rre = None
    if ground_truth_rotations_deg is not None and rotations is not None:
        if len(ground_truth_rotations_deg) != len(rotations):
            raise ValueError(
                f"{len(ground_truth_rotations_deg)} Ground-Truth-Rotationen != {len(rotations)} "
                f"Trajektorien-Frames ({reference_points_path} vs. {args.trajectory})"
            )
        R_gt = np.array([rotation_deg_to_matrix(a) for a in ground_truth_rotations_deg])
        R_est = np.array(rotations, dtype=float)
        rre = relative_rotation_error(R_est, R_gt, delta=args.rpe_delta)

    n_panels = 3 if rre is not None else 2
    fig, axes = plt.subplots(n_panels, 1, figsize=(8, 3 * n_panels), sharex=True)

    axes[0].plot(distance, ate["per_frame"], "-o", color="tab:blue", markersize=4)
    axes[0].axhline(ate["rmse"], color="tab:blue", linestyle=":", alpha=0.6, label=f"RMSE={ate['rmse']:.3f}m")
    axes[0].set_ylabel("ATE (m)")
    axes[0].set_title("Absolute Trajectory Error über die zurückgelegte Strecke")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)

    rpe_distance = distance[args.rpe_delta :]
    axes[1].plot(rpe_distance, rpe["per_step"], "-o", color="tab:orange", markersize=4)
    axes[1].axhline(rpe["rmse"], color="tab:orange", linestyle=":", alpha=0.6, label=f"RMSE={rpe['rmse']:.3f}m")
    axes[1].set_ylabel(f"RPE Translation (m, Δ={args.rpe_delta})")
    axes[1].set_title("Relative Pose Error (Translation) über die zurückgelegte Strecke")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    if rre is not None:
        axes[2].plot(rpe_distance, rre["per_step"], "-o", color="tab:green", markersize=4)
        axes[2].axhline(rre["rmse"], color="tab:green", linestyle=":", alpha=0.6, label=f"RMSE={rre['rmse']:.2f}°")
        axes[2].set_ylabel(f"RPE Rotation (°, Δ={args.rpe_delta})")
        axes[2].set_title("Relative Pose Error (Rotation) über die zurückgelegte Strecke")
        axes[2].legend(fontsize=8)
        axes[2].grid(True, alpha=0.3)

    axes[-1].set_xlabel("Zurückgelegte Strecke, Ground Truth (m)")
    fig.suptitle(f"Fehlerentwicklung: {args.trajectory.parent.name}")
    fig.tight_layout()

    output = args.output or args.trajectory.parent / "error_growth.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Plot gespeichert: {output}")


if __name__ == "__main__":
    main()
