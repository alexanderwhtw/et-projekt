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
from src.localization.pose_estimation import ImplausiblePoseError  # noqa: E402
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
    parser.add_argument(
        "--max-translation-m",
        type=float,
        default=None,
        help="Plausibilitaets-Filter: maximale Translation (m) pro Schritt, groessere Sprünge "
        "werden als Fehlmatch verworfen (Frame wird uebersprungen, siehe docs/decisions.md 2026-09-21). "
        "Default: kein Filter.",
    )
    parser.add_argument(
        "--max-rotation-deg",
        type=float,
        default=None,
        help="Plausibilitaets-Filter: maximale Rotation (Grad) pro Schritt, siehe --max-translation-m.",
    )
    parser.add_argument(
        "--ratio-threshold",
        type=float,
        default=0.75,
        help="Lowe's-Ratio-Schwellwert fuer temporales Matching (Default: 0.75).",
    )
    parser.add_argument(
        "--ransac-inlier-threshold",
        type=float,
        default=0.02,
        help="RANSAC-Inlier-Schwellwert in Metern (Default: 0.02).",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Suffix fuer den Ergebnisordner (results/measurements/<datum>_vo_sequence_test_<tag>/), "
        "um mehrere Laeufe am selben Tag nicht zu ueberschreiben.",
    )
    parser.add_argument(
        "--depth-weighted",
        action="store_true",
        help="Gewichtete Kabsch/Procrustes-Anpassung: Punkte werden im finalen RANSAC-Refit "
        "nach 1/Z^depth-weight-power gewichtet statt gleich behandelt (siehe depth_weights(), "
        "docs/decisions.md 2026-09-23) -- daempft den Einfluss ferner, tiefenungenauer Punkte.",
    )
    parser.add_argument(
        "--depth-weight-power",
        type=float,
        default=4.0,
        help="Exponent fuer --depth-weighted (Default 4.0 = inverse Varianz, siehe Delta_Z ~ Z^2 "
        "Fehlerfortpflanzung in docs/decisions.md 2026-09-23).",
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
    poses = [pose]
    print(f"  Frame 0: [{pose[0, 3]:+.4f}, {pose[1, 3]:+.4f}, {pose[2, 3]:+.4f}]")

    n_skipped = 0
    skip_streak = 0
    for frame_index, entry in enumerate(entries[1:], start=1):
        image_L, image_R = load_rectified(entry)
        # bound scales with consecutive skips -- see src/localization/vo_pipeline.py::run_vo_pipeline()
        # docstring / docs/decisions.md (2026-09-21): a fixed bound cascades into total tracking loss.
        scale = 1 + skip_streak
        effective_max_translation_m = None if args.max_translation_m is None else args.max_translation_m * scale
        effective_max_rotation_deg = None if args.max_rotation_deg is None else args.max_rotation_deg * scale
        try:
            new_pose, new_points, new_descriptors = step_vo_pipeline(
                image_L,
                image_R,
                P_L,
                P_R,
                pose,
                points,
                descriptors,
                ratio_threshold=args.ratio_threshold,
                ransac_inlier_threshold=args.ransac_inlier_threshold,
                seed=args.seed,
                max_translation_m=effective_max_translation_m,
                max_rotation_deg=effective_max_rotation_deg,
                use_depth_weighting=args.depth_weighted,
                depth_weight_power=args.depth_weight_power,
            )
        except ImplausiblePoseError as e:
            # skip: repeat prev pose, keep matching against the last trusted state
            # (see run_vo_pipeline() docstring, src/localization/vo_pipeline.py)
            n_skipped += 1
            skip_streak += 1
            poses.append(pose)
            print(f"  Frame {frame_index}: UEBERSPRUNGEN ({e})")
            continue
        except RuntimeError as e:
            raise RuntimeError(f"frame {frame_index}: {e}") from e
        skip_streak = 0
        pose, points, descriptors = new_pose, new_points, new_descriptors
        poses.append(pose)
        print(f"  Frame {frame_index}: [{pose[0, 3]:+.4f}, {pose[1, 3]:+.4f}, {pose[2, 3]:+.4f}]")
    if n_skipped:
        print(f"\n{n_skipped} Frame(s) durch Plausibilitaets-Filter uebersprungen.")

    positions = np.array([pose[:3, 3] for pose in poses])
    rotations = np.array([pose[:3, :3] for pose in poses])

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
    folder_name = f"{today}_vo_sequence_test" + (f"_{args.tag}" if args.tag else "")
    output_path = RESULTS_DIR / folder_name / "trajectory.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(
            {
                "sequence_dir": str(args.sequence_dir),
                "calibration": str(args.calibration),
                "seed": args.seed,
                "ratio_threshold": args.ratio_threshold,
                "ransac_inlier_threshold": args.ransac_inlier_threshold,
                "max_translation_m": args.max_translation_m,
                "max_rotation_deg": args.max_rotation_deg,
                "depth_weighted": args.depth_weighted,
                "depth_weight_power": args.depth_weight_power if args.depth_weighted else None,
                "n_skipped": n_skipped,
                "positions": [p.tolist() for p in positions],
                "rotations": [r.tolist() for r in rotations],
            },
            f,
            default_flow_style=None,
            sort_keys=False,
        )
    print(f"\nErgebnis gespeichert: {output_path}")


if __name__ == "__main__":
    main()
