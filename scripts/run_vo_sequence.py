"""VO-Pipeline auf einer echten Bildsequenz: Kalibrierung laden -> Sequenz
laden & rektifizieren -> Frame fuer Frame verarbeiten (vo_pipeline.init_vo_step()
+ step_vo_pipeline()) -> Trajektorie gegen Ground-Truth-Wegpunkte
(<sequence-dir>/ground_truth.yaml) vergleichen.

Erster echter End-to-End-Test der VO-Pipeline (bisher nur an synthetischen
Daten verifiziert, siehe docs/decisions.md, 2026-09-07/2026-09-08) --
Sanity-Check, keine formale ATE/RPE-Auswertung (siehe stattdessen
scripts/evaluate_trajectory.py, Phase 3).

Frame-fuer-Frame-Verarbeitung statt eines einzelnen run_vo_pipeline()-Batch-
Aufrufs (Umstellung 2026-09-16, siehe docs/decisions.md, Live-VO-
Umstellung): Bildquelle ist hier weiterhin die Platte (Sequenz bereits
aufgenommen), aber die Verarbeitungsschleife ist identisch zu der, die eine
Live-Aufnahme (Kamera -> sofort verarbeiten -> Zwischenstand ausgeben)
verwenden wird -- nur die Bildquelle (Datei vs. camera.capture_frame())
unterscheidet sich.

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
from src.localization.vo_pipeline import init_vo_step, step_vo_pipeline  # noqa: E402

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
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="RANSAC-Seed fuer reproduzierbare Ergebnisse (Default: 0). "
        "Ohne festen Seed schwankt vor allem der Fehler bei merkmalsarmen Frames stark "
        "zwischen Laeufen, siehe docs/decisions.md (2026-09-16).",
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

    def load_rectified(entry: dict) -> tuple[np.ndarray, np.ndarray]:
        left = cv2.imread(str(entry["left_path"]), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(entry["right_path"]), cv2.IMREAD_GRAYSCALE)
        left_rect = cv2.remap(left, map_x_L, map_y_L, cv2.INTER_LINEAR)
        right_rect = cv2.remap(right, map_x_R, map_y_R, cv2.INTER_LINEAR)
        return left_rect, right_rect

    P_L, P_R = calib["rectification"]["P1"], calib["rectification"]["P2"]

    # Frame-fuer-Frame statt Batch (siehe Docstring oben): Bildquelle ist hier
    # die Platte, aber diese Schleife ist identisch zu der einer spaeteren
    # Live-Aufnahme -- Pose direkt nach jedem Frame verfuegbar/ausgegeben,
    # nicht erst am Ende der ganzen Sequenz.
    print("\nGeschaetzte Trajektorie (x, y, z) in Metern, Ursprung = Frame 0:")
    pose, points, descriptors = init_vo_step(*load_rectified(entries[0]), P_L, P_R)
    positions = [pose[:3, 3]]
    print(f"  Frame 0: [{positions[0][0]:+.4f}, {positions[0][1]:+.4f}, {positions[0][2]:+.4f}]")

    for frame_index, entry in enumerate(entries[1:], start=1):
        image_L, image_R = load_rectified(entry)
        try:
            pose, points, descriptors = step_vo_pipeline(
                image_L, image_R, P_L, P_R, pose, points, descriptors, seed=args.seed
            )
        except RuntimeError as e:
            raise RuntimeError(f"frame {frame_index}: {e}") from e
        pos = pose[:3, 3]
        positions.append(pos)
        print(f"  Frame {frame_index}: [{pos[0]:+.4f}, {pos[1]:+.4f}, {pos[2]:+.4f}]")

    positions = np.array(positions)

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
                "seed": args.seed,
                "positions": [p.tolist() for p in positions],
            },
            f,
            default_flow_style=None,
            sort_keys=False,
        )
    print(f"\nErgebnis gespeichert: {output_path}")


if __name__ == "__main__":
    main()
