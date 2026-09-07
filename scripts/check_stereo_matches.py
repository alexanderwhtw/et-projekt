"""Visueller Sanity-Check: Feature-Matches zwischen linkem und rechtem Bild.

Zeichnet Verbindungslinien zwischen zueinander gehoerenden Merkmalen in L/R
(match_stereo_pairs()) -- fuer schnelles Nachvollziehen und als Abbildung im
Abschlussbericht.

WICHTIG: match_stereo_pairs() setzt rektifizierte Bilder voraus (horizontale
Epipolarlinien). Die echten Kamerabilder sind noch NICHT rektifiziert (Phase 1
Kalibrierung/Rektifizierung ist noch nicht implementiert, siehe CLAUDE.md) --
das Demo mit dem echten Bild nutzt daher bewusst ein groszuegiges max_y_diff
(Roll-Verkippung ~2,25 Grad / bis zu ~22px, siehe docs/decisions.md) und dient
nur der Anschauung, nicht als Genauigkeitsnachweis.

Nutzung:
    python scripts/check_stereo_matches.py [--image PATH] [--output PATH]
                                            [--max-y-diff PX] [--n-features N]

Ohne --image: nutzt das erste Bild aus cal/bilder/ (lokale Ad-hoc-Testauf-
nahmen, gitignored, falls vorhanden; das Stereo-Rohbild ist ein 2560x800-
Frame mit L/R nebeneinander, siehe docs/decisions.md) oder generiert sonst
ein synthetisches Stereo-Paar mit bekannter, konstanter Disparitaet.
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.localization.features import detect_features  # noqa: E402
from src.localization.stereo_depth import match_stereo_pairs  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "stereo_matches_demo.png"


def _find_demo_image() -> Path | None:
    """Sucht ein Stereo-Rohbild (2560x800, L+R nebeneinander) in cal/bilder/."""
    demo_dir = REPO_ROOT / "cal" / "bilder"
    if not demo_dir.is_dir():
        return None
    candidates = sorted(demo_dir.glob("*raw.png"))
    return candidates[0] if candidates else None


def _make_synthetic_stereo_pair(size: int = 300, disparity: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Texturierte Szene mit konstanter, bekannter Disparitaet (fronto-
    parallele Ebene) -- deterministisch (fester Seed)."""
    rng = np.random.default_rng(seed=42)
    left = np.full((size, size), 60, dtype=np.uint8)

    for _ in range(15):
        center = tuple(int(v) for v in rng.integers(40, size - 40, size=2))
        radius = int(rng.integers(8, 20))
        color = int(rng.integers(0, 255))
        cv2.circle(left, center, radius, color, thickness=-1)

    # right image = left image shifted left by `disparity` px (same content,
    # so every feature reappears on the same row with positive disparity)
    right = np.roll(left, -disparity, axis=1)
    return left, right


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=None, help="Pfad zu einem Stereo-Rohbild (L+R nebeneinander)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Pfad fuer das annotierte Ausgabebild")
    parser.add_argument("--max-y-diff", type=float, default=2.0, help="Max. Zeilenversatz fuer einen gueltigen Match (px)")
    parser.add_argument("--n-features", type=int, default=500, help="Max. Anzahl Merkmale (ORB nfeatures)")
    args = parser.parse_args()

    image_path = args.image or _find_demo_image()

    if image_path is not None:
        combined = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if combined is None:
            raise FileNotFoundError(f"Bild konnte nicht geladen werden: {image_path}")
        half = combined.shape[1] // 2
        left, right = combined[:, :half], combined[:, half:]
        max_y_diff = max(args.max_y_diff, 25.0)  # unrektifiziert: Roll-Verkippung tolerieren, siehe docs/decisions.md
        print(f"Verwende Bild: {image_path} (Stereo-Rohbild, {left.shape[1]}x{left.shape[0]} pro Haelfte)")
        print("Hinweis: Bild ist noch nicht rektifiziert -> max_y_diff grosszuegig gesetzt.")
    else:
        left, right = _make_synthetic_stereo_pair()
        max_y_diff = args.max_y_diff
        print("Kein Testbild gefunden - verwende synthetisches Stereo-Paar (bekannte Disparitaet).")

    keypoints_L, descriptors_L = detect_features(left, n_features=args.n_features)
    keypoints_R, descriptors_R = detect_features(right, n_features=args.n_features)
    matches = match_stereo_pairs(keypoints_L, descriptors_L, keypoints_R, descriptors_R, max_y_diff=max_y_diff)

    print(f"{len(keypoints_L)}/{len(keypoints_R)} Merkmale in L/R, {len(matches)} gueltige Stereo-Matches.")

    annotated = cv2.drawMatches(
        left, keypoints_L, right, keypoints_R, matches, None,
        matchColor=(0, 255, 0), singlePointColor=(0, 0, 255),
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), annotated)
    print(f"Annotiertes Bild gespeichert: {args.output}")


if __name__ == "__main__":
    main()
