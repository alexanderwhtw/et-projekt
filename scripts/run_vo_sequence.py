"""VO-Pipeline auf einer echten Bildsequenz: Kalibrierung laden -> Sequenz
laden & rektifizieren -> vo_pipeline.run_vo_pipeline() -> Trajektorie
gegen Ground-Truth-Wegpunkte (<sequence-dir>/ground_truth.yaml) vergleichen.

Erster echter End-to-End-Test der VO-Pipeline (bisher nur an synthetischen
Daten verifiziert, siehe docs/decisions.md, 2026-09-07/2026-09-08) --
Sanity-Check, keine formale ATE/RPE-Auswertung (die ist Phase 3).

Ground-Truth liegt seit 2026-09-15 pro Sequenz direkt neben den Bildern
(data/vo_sequences/<name>/ground_truth.yaml), nicht mehr in einer globalen
data/reference_points.yaml -- siehe docs/decisions.md.

Nutzung:
    python scripts/run_vo_sequence.py --sequence-dir data/vo_sequences/2026-09-08_tisch_translation \
                                       [--calibration results/calibration/2026-09-07_calibration.yaml] \
                                       [--reference-points PATH]  # Default: <sequence-dir>/ground_truth.yaml
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.io import load_calibration_result  # noqa: E402
from src.calibration.rectification import compute_rectification_maps  # noqa: E402
from src.localization.trajectory import positions_from_poses  # noqa: E402
from src.localization.vo_pipeline import run_vo_pipeline  # noqa: E402

DEFAULT_CALIBRATION = REPO_ROOT / "results" / "calibration" / "2026-09-07_calibration.yaml"
RESULTS_DIR = REPO_ROOT / "results" / "measurements"


def load_sequence_manifest(directory: Path) -> list[dict]:
    """Parse a VO sequence manifest (index/position_cm/notiz/shutter/gain/timestamp,
    see scripts/capture_vo_frame.py), in index order."""
    manifest_path = directory / "manifest.csv"
    entries = []
    with open(manifest_path, newline="") as f:
        for row in csv.DictReader(f):
            index = int(row["index"])
            entries.append(
                {
                    **row,
                    "left_path": directory / f"left_{index:03d}.png",
                    "right_path": directory / f"right_{index:03d}.png",
                }
            )
    entries.sort(key=lambda e: int(e["index"]))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence-dir", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument(
        "--reference-points",
        type=Path,
        default=None,
        help="Default: <sequence-dir>/ground_truth.yaml (Ground-Truth liegt pro Sequenz neben den Bildern)",
    )
    args = parser.parse_args()
    reference_points_path = args.reference_points or (args.sequence_dir / "ground_truth.yaml")

    calib = load_calibration_result(args.calibration)
    image_size = calib["image_size"]
    map_x_L, map_y_L = compute_rectification_maps(
        calib["left"]["K"], calib["left"]["dist"], calib["rectification"]["R1"], calib["rectification"]["P1"], image_size
    )
    map_x_R, map_y_R = compute_rectification_maps(
        calib["right"]["K"], calib["right"]["dist"], calib["rectification"]["R2"], calib["rectification"]["P2"], image_size
    )

    entries = load_sequence_manifest(args.sequence_dir)
    print(f"{len(entries)} Bildpaare in der Sequenz ({args.sequence_dir}).")

    stereo_frames = []
    for entry in entries:
        left = cv2.imread(str(entry["left_path"]), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(entry["right_path"]), cv2.IMREAD_GRAYSCALE)
        left_rect = cv2.remap(left, map_x_L, map_y_L, cv2.INTER_LINEAR)
        right_rect = cv2.remap(right, map_x_R, map_y_R, cv2.INTER_LINEAR)
        stereo_frames.append((left_rect, right_rect))

    P_L, P_R = calib["rectification"]["P1"], calib["rectification"]["P2"]

    poses = run_vo_pipeline(stereo_frames, P_L, P_R)
    positions = positions_from_poses(poses)

    print("\nGeschaetzte Trajektorie (x, y, z) in Metern, Ursprung = Frame 0:")
    for i, pos in enumerate(positions):
        print(f"  Frame {i}: [{pos[0]:+.4f}, {pos[1]:+.4f}, {pos[2]:+.4f}]")

    if reference_points_path.exists():
        ref_data = yaml.safe_load(open(reference_points_path))
        ref_points = list(ref_data.get("points", {}).values())
    else:
        print(f"\nHinweis: keine Ground-Truth-Datei gefunden ({reference_points_path}) -- kein Vergleich.")
        ref_points = []
    if ref_points and len(ref_points) == len(positions):
        print("\nVergleich geschaetzt vs. Massband-Ground-Truth:")
        errors = []
        for i, (pos, ref) in enumerate(zip(positions, ref_points)):
            ref = np.array(ref, dtype=float)
            err = np.linalg.norm(pos - ref)
            errors.append(err)
            print(f"  Frame {i}: geschaetzt x={pos[0]:+.4f}  ground-truth x={ref[0]:+.4f}  |Fehler|={err * 100:.1f}cm")
        print(f"\nMittlerer Positionsfehler: {np.mean(errors) * 100:.1f}cm, Max: {np.max(errors) * 100:.1f}cm")
    elif reference_points_path.exists():
        print(
            f"\nWARNUNG: Anzahl Frames ({len(positions)}) != Anzahl Ground-Truth-Punkte "
            f"({len(ref_points)}) -- kein automatischer Vergleich."
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    output_path = RESULTS_DIR / f"{today}_vo_sequence_test" / "trajectory.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(
            {
                "sequence_dir": str(args.sequence_dir),
                "calibration": str(args.calibration),
                "positions": [p.tolist() for p in positions],
            },
            f,
            default_flow_style=None,
            sort_keys=False,
        )
    print(f"\nErgebnis gespeichert: {output_path}")


if __name__ == "__main__":
    main()
