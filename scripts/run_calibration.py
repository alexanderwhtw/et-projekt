"""Kalibrier-Pipeline auf echten Aufnahmen: Manifest laden -> Ecken erkennen
-> Intrinsics (L, R) -> Extrinsics -> Rektifizierung -> Ergebnis speichern.

Verkettet die einzeln getesteten Bausteine aus src/calibration/ (jeder fuer
sich mit synthetischer Ground-Truth-Geometrie verifiziert, siehe
tests/test_corners.py, test_intrinsics.py, test_extrinsics.py,
test_rectification.py) auf einen echten Datensatz. Bildpaare, in denen das
Muster nicht in beiden Haelften gefunden wird, werden uebersprungen (mit
Warnung), nicht stillschweigend ignoriert.

Nutzung:
    python scripts/run_calibration.py [--cols 6] [--rows 7] [--square-size 0.024]
                                       [--alpha 0.0]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.corners import find_checkerboard_corners, generate_object_points  # noqa: E402
from src.calibration.extrinsics import calibrate_extrinsics  # noqa: E402
from src.calibration.intrinsics import calibrate_intrinsics, compute_per_image_reprojection_errors  # noqa: E402
from src.calibration.io import load_calibration_manifest, save_calibration_result  # noqa: E402
from src.calibration.rectification import compute_rectification  # noqa: E402

CALIBRATION_IMAGES_DIR = REPO_ROOT / "data" / "calibration_images"
RESULTS_DIR = REPO_ROOT / "results" / "calibration"
MEASURED_BASELINE_M = 0.06  # Maßband-Referenz, siehe docs/decisions.md, 2026-09-02


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--rows", type=int, default=7)
    parser.add_argument("--square-size", type=float, default=0.024, help="Kantenlaenge eines Feldes (m)")
    parser.add_argument("--alpha", type=float, default=0.0, help="Rektifizierung: 0=nur gueltige Pixel, 1=alle Pixel")
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)

    entries = load_calibration_manifest(CALIBRATION_IMAGES_DIR)
    print(f"{len(entries)} Bildpaare im Manifest gefunden.")

    object_points_list, image_points_L_list, image_points_R_list = [], [], []
    image_size = None
    skipped = []

    for entry in entries:
        left = cv2.imread(str(entry["left_path"]), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(entry["right_path"]), cv2.IMREAD_GRAYSCALE)
        if image_size is None:
            image_size = (left.shape[1], left.shape[0])  # (width, height)

        corners_L = find_checkerboard_corners(left, pattern_size)
        corners_R = find_checkerboard_corners(right, pattern_size)
        if corners_L is None or corners_R is None:
            skipped.append(entry["index"])
            continue

        object_points_list.append(generate_object_points(pattern_size, args.square_size))
        image_points_L_list.append(corners_L)
        image_points_R_list.append(corners_R)

    print(f"{len(object_points_list)} Paare verwendbar, {len(skipped)} uebersprungen (Muster nicht erkannt): {skipped}")
    if len(object_points_list) < 3:
        print("Zu wenige verwendbare Bildpaare fuer eine Kalibrierung (mindestens 3 noetig).")
        return

    K_L, dist_L, error_L = calibrate_intrinsics(object_points_list, image_points_L_list, image_size)
    K_R, dist_R, error_R = calibrate_intrinsics(object_points_list, image_points_R_list, image_size)
    print(f"\nIntrinsics L: Reprojection Error {error_L:.3f}px")
    print(f"Intrinsics R: Reprojection Error {error_R:.3f}px")

    per_image_L = compute_per_image_reprojection_errors(object_points_list, image_points_L_list, K_L, dist_L)
    per_image_R = compute_per_image_reprojection_errors(object_points_list, image_points_R_list, K_R, dist_R)
    used_indices = [e["index"] for e in entries if e["index"] not in skipped]
    for idx, err_l, err_r in zip(used_indices, per_image_L, per_image_R):
        flag = " <-- auffaellig" if max(err_l, err_r) > 1.0 else ""
        print(f"  Bild {idx}: L={err_l:.3f}px R={err_r:.3f}px{flag}")

    R, T, error_stereo = calibrate_extrinsics(
        object_points_list, image_points_L_list, image_points_R_list, K_L, dist_L, K_R, dist_R, image_size
    )
    baseline = (T[0] ** 2 + T[1] ** 2 + T[2] ** 2) ** 0.5
    print(f"\nExtrinsics: Reprojection Error {error_stereo:.3f}px")
    print(f"Baseline: {baseline * 1000:.2f}mm (Massband-Referenz: {MEASURED_BASELINE_M * 1000:.0f}mm)")

    R1, R2, P1, P2, Q = compute_rectification(K_L, dist_L, K_R, dist_R, image_size, R, T, alpha=args.alpha)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    output_path = RESULTS_DIR / f"{today}_calibration.yaml"
    save_calibration_result(
        output_path,
        date=today,
        image_size=image_size,
        K_L=K_L, dist_L=dist_L, error_L=error_L,
        K_R=K_R, dist_R=dist_R, error_R=error_R,
        R=R, T=T, error_stereo=error_stereo,
        R1=R1, R2=R2, P1=P1, P2=P2, Q=Q,
    )
    print(f"\nErgebnis gespeichert: {output_path}")


if __name__ == "__main__":
    main()
