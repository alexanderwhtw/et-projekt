"""Interaktive Aufnahme-Session: Kalibrierbilder fuer data/calibration_images/.

MUSS auf dem Pi laufen (braucht rpicam-still + die echte Kamera, siehe
src/capture/camera.py) -- auf dem Host-Rechner nicht lauffaehig.

Ablauf pro Aufnahme:
  1. Schachbrett positionieren (Distanz/Pose kurz notieren)
  2. Enter druecken -> Aufnahme wird ausgeloest
  3. Sofortige Eckenerkennung als Live-Check: Muster in L UND R gefunden?
     Wenn nicht -> Warnung, damit die schlechte Aufnahme direkt auffaellt
     (nicht erst beim spaeteren Kalibrieren). Schlechte Aufnahmen bleiben
     liegen (kein automatisches Ueberschreiben) -- bei Bedarf die
     zugehoerigen left_NNN.png/right_NNN.png + Manifest-Zeile manuell
     entfernen.

Nutzung:
    python scripts/capture_calibration_images.py [--shutter US] [--gain G]
                                                  [--cols N] [--rows N]
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
    parser.add_argument("--shutter", type=int, default=10000, help="Belichtungszeit in Mikrosekunden (siehe docs/decisions.md)")
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--cols", type=int, default=6, help="Anzahl innerer Ecken (Spalten)")
    parser.add_argument("--rows", type=int, default=7, help="Anzahl innerer Ecken (Zeilen)")
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)

    print(f"Speicherort: {OUTPUT_DIR}")
    print(f"Settings: shutter={args.shutter}us gain={args.gain}, Muster {pattern_size}")
    print("Enter = Aufnahme ausloesen, 'q' + Enter = beenden.\n")

    while True:
        notiz = input("Notiz zur Pose (z.B. '1m frontal', 'Ecke gekippt') oder 'q' zum Beenden: ").strip()
        if notiz.lower() == "q":
            break
        distanz_raw = input("Geschaetzte Distanz in m (optional, Enter zum Ueberspringen): ").strip()
        distanz_m = float(distanz_raw) if distanz_raw else ""

        input("Bereit? Enter druecken fuer die Aufnahme...")
        index = capture_indexed_pair(
            OUTPUT_DIR,
            args.shutter,
            args.gain,
            MANIFEST_FIELDNAMES,
            extra_manifest_fields={"distanz_m": distanz_m, "notiz": notiz},
        )

        left = cv2.imread(str(OUTPUT_DIR / f"left_{index:03d}.png"), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(OUTPUT_DIR / f"right_{index:03d}.png"), cv2.IMREAD_GRAYSCALE)
        corners_L = find_checkerboard_corners(left, pattern_size)
        corners_R = find_checkerboard_corners(right, pattern_size)

        status_L = f"{len(corners_L)} Ecken" if corners_L is not None else "NICHT gefunden"
        status_R = f"{len(corners_R)} Ecken" if corners_R is not None else "NICHT gefunden"
        print(f"  -> Bild {index}: L={status_L}, R={status_R}")
        if corners_L is None or corners_R is None:
            print(f"  WARNUNG: Muster nicht in beiden Haelften erkannt (left_{index:03d}.png/right_{index:03d}.png).")
            print("  Aufnahme wiederholen empfohlen. Diese Dateien bleiben liegen - bei Bedarf manuell loeschen.")
        print()

    print(f"Fertig. Bilder + manifest.csv liegen in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
