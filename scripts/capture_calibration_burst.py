"""Burst-Aufnahme fuer die Kalibrier-Bildserie: statt jede Aufnahme einzeln
manuell auszuloesen, wird automatisch alle --interval Sekunden ein
Bildpaar aufgenommen, waehrend das Schachbrett von Hand durch den Raum
bewegt wird (naeher/weiter, gekippt, auch unten/oben im Bild) -- deutlich
schneller und mit mehr Posen-/Distanz-Varianz als Einzelaufnahmen, siehe
docs/decisions.md, 2026-09-15 (Fehlerbetrachtung Tiefenfehler).

Bewusst KEINE Pose-Beschreibung pro Bild waehrend der Aufnahme -- alle
Bilder dieser Session bekommen denselben Platzhalter in der
manifest.csv-Spalte "notiz". Die Beschreibung einzelner Posen (falls
gewuenscht) erfolgt nachtraeglich von Hand anhand der gespeicherten
Bilder, blockiert die Kalibrierung aber nicht: run_calibration.py wertet
"notiz"/"distanz_m" nicht aus, ueberspringt aber automatisch Bildpaare
ohne erkanntes Muster.

Ergaenzt die bestehenden Kalibrierbilder in data/calibration_images/
(next_free_index() haengt an, ueberschreibt nichts) -- kein neues
Verzeichnis noetig, solange der Kamera-Mount unveraendert bleibt.

MUSS auf dem Pi laufen (braucht rpicam-still + die echte Kamera).

Nutzung:
    python scripts/capture_calibration_burst.py --count 25 --interval 10
                                                  [--notiz "burst 2026-09-15"]
                                                  [--shutter 10000] [--gain 1.0]
                                                  [--cols 6] [--rows 7]
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.corners import find_checkerboard_corners  # noqa: E402
from src.capture.session import capture_indexed_pair  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "data" / "calibration_images"
MANIFEST_FIELDNAMES = ["index", "distanz_m", "notiz", "shutter", "gain", "timestamp"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, required=True, help="Anzahl Aufnahmen")
    parser.add_argument("--interval", type=float, default=10.0, help="Sekunden Wartezeit vor jeder Aufnahme")
    parser.add_argument(
        "--notiz",
        default="burst",
        help="Platzhalter-Notiz fuer alle Bilder dieser Session (Pose-Details spaeter von Hand ergaenzen)",
    )
    parser.add_argument("--shutter", type=int, default=10000)
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--cols", type=int, default=6, help="Anzahl innerer Ecken (Spalten)")
    parser.add_argument("--rows", type=int, default=7, help="Anzahl innerer Ecken (Zeilen)")
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)

    print(
        f"Burst-Aufnahme: {args.count} Bilder, je {args.interval:.0f}s Abstand "
        f"(erste Aufnahme in {args.interval:.0f}s) -- Schachbrett jetzt in Position bringen."
    )

    ok_count = 0
    for i in range(args.count):
        time.sleep(args.interval)
        index = capture_indexed_pair(
            OUTPUT_DIR,
            args.shutter,
            args.gain,
            MANIFEST_FIELDNAMES,
            extra_manifest_fields={"distanz_m": "", "notiz": args.notiz},
        )
        left = cv2.imread(str(OUTPUT_DIR / f"left_{index:03d}.png"), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(OUTPUT_DIR / f"right_{index:03d}.png"), cv2.IMREAD_GRAYSCALE)
        corners_L = find_checkerboard_corners(left, pattern_size)
        corners_R = find_checkerboard_corners(right, pattern_size)
        found = corners_L is not None and corners_R is not None
        ok_count += int(found)
        status = "OK" if found else "NICHT erkannt"
        print(f"  [{i + 1}/{args.count}] Bild {index}: {status}")

    print(f"\nFertig: {ok_count}/{args.count} Bildpaare mit erkanntem Muster in beiden Haelften.")
    print("Zur Nachbearbeitung: data/calibration_images/manifest.csv, Spalte 'notiz', optional von Hand ergaenzen.")
    if ok_count < args.count:
        print(f"({args.count - ok_count} Bildpaare ohne erkanntes Muster -- werden von run_calibration.py automatisch uebersprungen.)")


if __name__ == "__main__":
    main()
