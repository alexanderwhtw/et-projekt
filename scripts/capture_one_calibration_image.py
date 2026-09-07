"""Nicht-interaktive Einzelaufnahme fuer die Kalibrier-Bildserie.

Gegenstueck zu capture_calibration_images.py fuer den Fall, dass jede
Aufnahme einzeln per Aufruf ausgeloest wird (z.B. ferngesteuert ueber SSH,
statt interaktiv mit Enter-Tastendruck vor Ort) -- gleiche zugrunde
liegende Logik (session.capture_indexed_pair), gleiche sofortige
Eckenerkennung als Feedback.

MUSS auf dem Pi laufen (braucht rpicam-still + die echte Kamera).

Nutzung:
    python scripts/capture_one_calibration_image.py --notiz "1m frontal" [--distanz 1.0]
                                                      [--shutter 10000] [--gain 1.0]
                                                      [--cols 6] [--rows 7]
"""

import argparse
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.corners import find_checkerboard_corners  # noqa: E402
from src.capture.session import capture_indexed_pair  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "data" / "calibration_images"
MANIFEST_FIELDNAMES = ["index", "distanz_m", "notiz", "shutter", "gain", "timestamp"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notiz", required=True, help="Kurzbeschreibung der Pose")
    parser.add_argument("--distanz", type=float, default=None, help="Geschaetzte Distanz in m (optional)")
    parser.add_argument("--shutter", type=int, default=10000)
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--cols", type=int, default=6, help="Anzahl innerer Ecken (Spalten)")
    parser.add_argument("--rows", type=int, default=7, help="Anzahl innerer Ecken (Zeilen)")
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)

    index = capture_indexed_pair(
        OUTPUT_DIR,
        args.shutter,
        args.gain,
        MANIFEST_FIELDNAMES,
        extra_manifest_fields={"distanz_m": args.distanz if args.distanz is not None else "", "notiz": args.notiz},
    )

    left = cv2.imread(str(OUTPUT_DIR / f"left_{index:03d}.png"), cv2.IMREAD_GRAYSCALE)
    right = cv2.imread(str(OUTPUT_DIR / f"right_{index:03d}.png"), cv2.IMREAD_GRAYSCALE)
    corners_L = find_checkerboard_corners(left, pattern_size)
    corners_R = find_checkerboard_corners(right, pattern_size)

    status_L = f"{len(corners_L)} Ecken" if corners_L is not None else "NICHT gefunden"
    status_R = f"{len(corners_R)} Ecken" if corners_R is not None else "NICHT gefunden"
    print(f"Bild {index}: L={status_L}, R={status_R}")
    if corners_L is None or corners_R is None:
        print(f"WARNUNG: Muster nicht in beiden Haelften erkannt (left_{index:03d}.png/right_{index:03d}.png).")


if __name__ == "__main__":
    main()
