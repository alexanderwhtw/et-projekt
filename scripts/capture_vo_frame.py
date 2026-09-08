"""Nicht-interaktive Einzelaufnahme fuer eine VO-Testsequenz.

Gegenstueck zu capture_one_calibration_image.py fuer natuerliche VO-
Sequenzen: keine Schachbrett-Erkennung (die VO nutzt natuerliche Merkmale,
kein Board), stattdessen wird nur die Aufnahme ausgeloest und die Position
(z.B. lateraler Versatz in cm, per Massband gemessen) im Manifest
vermerkt.

MUSS auf dem Pi laufen (braucht rpicam-still + die echte Kamera).

Nutzung:
    python scripts/capture_vo_frame.py --sequence-dir data/vo_sequences/<name> \
                                        --position-cm 0 --notiz "Startposition" \
                                        [--shutter 10000] [--gain 1.0]
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.capture.session import capture_indexed_pair  # noqa: E402

MANIFEST_FIELDNAMES = ["index", "position_cm", "notiz", "shutter", "gain", "timestamp"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence-dir", type=Path, required=True, help="Zielverzeichnis fuer diese VO-Sequenz")
    parser.add_argument("--position-cm", type=float, required=True, help="Lateraler Versatz von der Startposition in cm (Massband-Ground-Truth)")
    parser.add_argument("--notiz", default="", help="Kurzbeschreibung der Pose")
    parser.add_argument("--shutter", type=int, default=10000)
    parser.add_argument("--gain", type=float, default=1.0)
    args = parser.parse_args()

    index = capture_indexed_pair(
        args.sequence_dir,
        args.shutter,
        args.gain,
        MANIFEST_FIELDNAMES,
        extra_manifest_fields={"position_cm": args.position_cm, "notiz": args.notiz},
    )
    print(f"Bild {index} gespeichert in {args.sequence_dir} (position_cm={args.position_cm})")


if __name__ == "__main__":
    main()
