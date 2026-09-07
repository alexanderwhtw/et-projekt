"""Visueller Sanity-Check: Schachbrett-Eckenerkennung.

Zeichnet erkannte Innenecken (find_checkerboard_corners()) ins Bild --
fuer schnelles Nachvollziehen und als Abbildung im Abschlussbericht.
Ersetzt das Ad-hoc-Skript cal/check_corners.py (gitignored) durch eine
Version, die die src/-Logik direkt nutzt.

Nutzung:
    python scripts/check_corner_detection.py [--image PATH] [--output PATH]
                                              [--cols N] [--rows N]

Ohne --image: nutzt das erste Bild aus cal/bilder/ (lokale Ad-hoc-Testauf-
nahmen, gitignored, linke Haelfte). ACHTUNG: diese Aufnahmen zeigen noch
das alte 7x7-Brett (vor dem Tag-4-Zuschnitt auf 6x7, siehe
docs/decisions.md, 2026-09-04) -- schlaegt die Erkennung mit dem aktuellen
Standard-Pattern (6,7) fehl, faellt das Skript auf ein synthetisches
Testbild zurueck.
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.corners import find_checkerboard_corners  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "corner_detection_demo.png"


def _find_demo_image() -> Path | None:
    demo_dir = REPO_ROOT / "cal" / "bilder"
    if not demo_dir.is_dir():
        return None
    candidates = sorted(demo_dir.glob("*raw.png"))
    return candidates[0] if candidates else None


def _make_synthetic_checkerboard(pattern_size: tuple[int, int], square_px: int = 60, margin_px: int = 60) -> np.ndarray:
    cols, rows = pattern_size
    n_squares_x, n_squares_y = cols + 1, rows + 1
    width = n_squares_x * square_px + 2 * margin_px
    height = n_squares_y * square_px + 2 * margin_px
    image = np.full((height, width), 255, dtype=np.uint8)
    for row in range(n_squares_y):
        for col in range(n_squares_x):
            if (row + col) % 2 == 0:
                y0 = margin_px + row * square_px
                x0 = margin_px + col * square_px
                image[y0 : y0 + square_px, x0 : x0 + square_px] = 0
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=None, help="Pfad zu einem Testbild")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cols", type=int, default=6, help="Anzahl innerer Ecken (Spalten)")
    parser.add_argument("--rows", type=int, default=7, help="Anzahl innerer Ecken (Zeilen)")
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)

    image_path = args.image or _find_demo_image()
    image = None
    if image_path is not None:
        loaded = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if loaded is None:
            raise FileNotFoundError(f"Bild konnte nicht geladen werden: {image_path}")
        image = loaded[:, : loaded.shape[1] // 2]  # linke Haelfte des Stereo-Rohbilds
        corners = find_checkerboard_corners(image, pattern_size)
        if corners is None:
            print(f"Muster {pattern_size} in {image_path.name} nicht gefunden - verwende synthetisches Testbild.")
            image = None

    if image is None:
        image = _make_synthetic_checkerboard(pattern_size)
        corners = find_checkerboard_corners(image, pattern_size)
        print("Synthetisches Testbild verwendet.")
    else:
        print(f"Verwende Bild: {image_path}")

    found = corners is not None
    print(f"Muster {pattern_size}: {'GEFUNDEN' if found else 'NICHT gefunden'}" + (f" ({len(corners)} Ecken)" if found else ""))

    annotated = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if found:
        cv2.drawChessboardCorners(annotated, pattern_size, corners, True)
    else:
        cv2.putText(annotated, "NOT FOUND", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), annotated)
    print(f"Annotiertes Bild gespeichert: {args.output}")


if __name__ == "__main__":
    main()
