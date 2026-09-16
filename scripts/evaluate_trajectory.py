"""Berechnet ATE/RPE fuer eine berechnete VO-Trajektorie gegen ihre Massband-
Ground-Truth und gibt einen Report aus (Konsole + optionale YAML-Datei).

Rein nachgelagerter Auswertungs-Output auf Basis bereits berechneter VO-
Ergebnisse -- kein Bestandteil des Lokalisierungsalgorithmus (siehe
docs/decisions.md, 2026-09-07). Nutzt dieselbe Trajectory-/Ground-Truth-
Ladelogik wie scripts/plot_trajectory_map.py.

Nutzung:
    python scripts/evaluate_trajectory.py \
        --trajectory results/measurements/2026-09-08_vo_sequence_test/trajectory.yaml \
        [--reference-points PATH]  # Default: <sequence-dir aus trajectory.yaml>/ground_truth.yaml
        [--rpe-delta N]            # Default: 1 (aufeinanderfolgende Frames)
        [--output PATH]            # Default: kein Report-File, nur Konsolenausgabe
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.metrics import absolute_trajectory_error, relative_pose_error  # noqa: E402


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
    parser.add_argument("--output", type=Path, default=None, help="Optional: Report als YAML speichern")
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

    ate = absolute_trajectory_error(positions, ground_truth)
    rpe = relative_pose_error(positions, ground_truth, delta=args.rpe_delta)

    print(f"Trajektorie: {args.trajectory}")
    print(f"Ground Truth: {reference_points_path}")
    print(f"Frames: {len(positions)}")
    print()
    print("ATE (Absolute Trajectory Error, m):")
    print(f"  pro Frame: {np.round(ate['per_frame'], 4).tolist()}")
    print(f"  RMSE={ate['rmse']:.4f}  Mean={ate['mean']:.4f}  Max={ate['max']:.4f}")
    print()
    print(f"RPE (Relative Pose Error, delta={args.rpe_delta}, m):")
    print(f"  pro Schritt: {np.round(rpe['per_step'], 4).tolist()}")
    print(f"  RMSE={rpe['rmse']:.4f}  Mean={rpe['mean']:.4f}  Max={rpe['max']:.4f}")

    if args.output:
        report = {
            "trajectory": str(args.trajectory),
            "ground_truth": str(reference_points_path),
            "n_frames": len(positions),
            "ate": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in ate.items()},
            "rpe": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in rpe.items()},
            "rpe_delta": args.rpe_delta,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            yaml.safe_dump(report, f, sort_keys=False)
        print(f"\nReport gespeichert: {args.output}")


if __name__ == "__main__":
    main()
