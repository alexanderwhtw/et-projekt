"""Phase 1 Validierung: erste Tiefenmessung vs. Maßband (siehe CLAUDE.md Roadmap).

Nimmt eine NEUE Stereo-Aufnahme des Schachbretts bei einer mit Massband
gemessenen Distanz auf (unabhaengig von den Kalibrieraufnahmen - keine
Zirkularitaet), rektifiziert sie mit einem gespeicherten Kalibrierergebnis,
erkennt die Schachbrett-Ecken in den rektifizierten Bildern, trianguliert
sie und vergleicht die berechnete Tiefe mit der gemessenen Distanz.

MUSS auf dem Pi laufen (braucht rpicam-still + die echte Kamera).

Nutzung:
    python scripts/measure_depth.py --distanz-m 1.20 [--notiz "Test 1,2m"]
                                     [--calibration results/calibration/2026-09-07_calibration.yaml]
                                     [--shutter 10000] [--gain 1.0] [--cols 6] [--rows 7]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.corners import find_checkerboard_corners  # noqa: E402
from src.calibration.io import load_calibration_result  # noqa: E402
from src.calibration.rectification import compute_rectification_maps  # noqa: E402
from src.capture.camera import capture_frame, split_stereo_frame  # noqa: E402

RESULTS_DIR = REPO_ROOT / "results" / "measurements"


def _latest_calibration() -> Path:
    candidates = sorted((REPO_ROOT / "results" / "calibration").glob("*_calibration.yaml"))
    if not candidates:
        raise FileNotFoundError("keine Kalibrierergebnisse in results/calibration/ gefunden")
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distanz-m", type=float, required=True, help="Mit Massband gemessene Distanz Kamera->Brett")
    parser.add_argument("--notiz", default="")
    parser.add_argument("--calibration", type=Path, default=None, help="Pfad zur Kalibrier-YAML (default: neueste in results/calibration/)")
    parser.add_argument("--shutter", type=int, default=10000)
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--rows", type=int, default=7)
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)

    calibration_path = args.calibration or _latest_calibration()
    calibration = load_calibration_result(calibration_path)
    print(f"Kalibrierung: {calibration_path.name}")

    today = date.today().isoformat()
    output_dir = RESULTS_DIR / f"{today}_depth_validation_{args.distanz_m:.2f}m".replace(".", "-", 1)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined_path = output_dir / "raw_combined.png"
    capture_frame(combined_path, args.shutter, args.gain)
    combined = cv2.imread(str(combined_path), cv2.IMREAD_GRAYSCALE)
    left, right = split_stereo_frame(combined)
    cv2.imwrite(str(output_dir / "left.png"), left)
    cv2.imwrite(str(output_dir / "right.png"), right)

    image_size = calibration["image_size"]
    map_L = compute_rectification_maps(
        calibration["left"]["K"], calibration["left"]["dist"],
        calibration["rectification"]["R1"], calibration["rectification"]["P1"], image_size,
    )
    map_R = compute_rectification_maps(
        calibration["right"]["K"], calibration["right"]["dist"],
        calibration["rectification"]["R2"], calibration["rectification"]["P2"], image_size,
    )
    rect_L = cv2.remap(left, *map_L, cv2.INTER_LINEAR)
    rect_R = cv2.remap(right, *map_R, cv2.INTER_LINEAR)
    cv2.imwrite(str(output_dir / "left_rectified.png"), rect_L)
    cv2.imwrite(str(output_dir / "right_rectified.png"), rect_R)

    corners_L = find_checkerboard_corners(rect_L, pattern_size)
    corners_R = find_checkerboard_corners(rect_R, pattern_size)
    if corners_L is None or corners_R is None:
        print("Muster nicht in beiden rektifizierten Haelften gefunden - Messung nicht moeglich.")
        return

    P1 = calibration["rectification"]["P1"]
    P2 = calibration["rectification"]["P2"]
    points_4d = cv2.triangulatePoints(P1, P2, corners_L.T.astype(np.float64), corners_R.T.astype(np.float64))
    points_3d = (points_4d[:3] / points_4d[3]).T

    depths = points_3d[:, 2]
    computed_depth = float(np.mean(depths))
    error_m = computed_depth - args.distanz_m
    error_pct = 100 * error_m / args.distanz_m

    print(f"\nGemessene Distanz (Massband): {args.distanz_m:.3f}m")
    print(f"Berechnete Tiefe (Mittel ueber {len(depths)} Eckpunkte): {computed_depth:.3f}m")
    print(f"  min={depths.min():.3f}m max={depths.max():.3f}m std={depths.std() * 1000:.1f}mm")
    print(f"Abweichung: {error_m * 1000:+.1f}mm ({error_pct:+.1f}%)")

    result = {
        "date": today,
        "notiz": args.notiz,
        "calibration_used": str(calibration_path.relative_to(REPO_ROOT)),
        "measured_distance_m": args.distanz_m,
        "computed_depth_mean_m": computed_depth,
        "computed_depth_min_m": float(depths.min()),
        "computed_depth_max_m": float(depths.max()),
        "computed_depth_std_mm": float(depths.std() * 1000),
        "error_mm": error_m * 1000,
        "error_pct": error_pct,
        "n_corners": int(len(depths)),
    }
    with open(output_dir / "result.yaml", "w") as f:
        yaml.safe_dump(result, f, sort_keys=False)
    print(f"\nErgebnis gespeichert: {output_dir}")


if __name__ == "__main__":
    main()
