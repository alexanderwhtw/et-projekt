"""Visueller Sanity-Check: ORB-Merkmale in einem Bild markieren.

Zeigt, welche Merkmale (Ecken/Texturen) detect_features() in einem Bild
findet — Kreisgröße = Skalierung, Linie = Orientierung des Deskriptors.
Für schnelles Nachvollziehen und als Abbildung im Abschlussbericht.

Nutzung:
    python scripts/check_features.py [--image PATH] [--output PATH] [--n-features N]

Ohne --image: nutzt das erste Bild aus cal/bilder/ (lokale Ad-hoc-Testauf-
nahmen, gitignored, falls vorhanden) oder generiert sonst ein synthetisches
Testbild, damit das Skript auch ohne echte Kamerabilder lauffähig ist.
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.localization.features import detect_features  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "features_demo.png"


def _find_demo_image() -> Path | None:
    """Sucht ein Beispielbild in cal/bilder/ (lokale Ad-hoc-Aufnahmen)."""
    demo_dir = REPO_ROOT / "cal" / "bilder"
    if not demo_dir.is_dir():
        return None
    candidates = sorted(demo_dir.glob("*raw.png"))
    return candidates[0] if candidates else None


def _make_synthetic_scene(size: int = 400) -> np.ndarray:
    """Texturiertes Testbild (Schachbrett + Kreise), falls kein echtes
    Bild verfügbar ist — deterministisch (fester Seed)."""
    rng = np.random.default_rng(seed=42)
    image = np.full((size, size), 60, dtype=np.uint8)

    square = 40
    for row in range(0, size, square):
        for col in range(0, size, square):
            if ((row // square) + (col // square)) % 2 == 0:
                image[row : row + square, col : col + square] = 220

    for _ in range(8):
        center = tuple(int(v) for v in rng.integers(30, size - 30, size=2))
        radius = int(rng.integers(10, 25))
        color = int(rng.integers(0, 255))
        cv2.circle(image, center, radius, color, thickness=-1)

    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=None, help="Pfad zu einem Testbild")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Pfad fuer das annotierte Ausgabebild")
    parser.add_argument("--n-features", type=int, default=500, help="Max. Anzahl Merkmale (ORB nfeatures)")
    args = parser.parse_args()

    image_path = args.image or _find_demo_image()

    if image_path is not None:
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"Bild konnte nicht geladen werden: {image_path}")
        print(f"Verwende Bild: {image_path}")
    else:
        image = _make_synthetic_scene()
        print("Kein Testbild gefunden - verwende synthetisches Demo-Bild.")

    keypoints, descriptors = detect_features(image, n_features=args.n_features)
    print(f"{len(keypoints)} Merkmale gefunden ({descriptors.shape[1]}-Byte-Deskriptoren).")

    annotated = cv2.drawKeypoints(
        image,
        keypoints,
        None,
        color=(0, 255, 0),
        flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), annotated)
    print(f"Annotiertes Bild gespeichert: {args.output}")


if __name__ == "__main__":
    main()
