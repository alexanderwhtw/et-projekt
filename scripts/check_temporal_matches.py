"""Visueller Sanity-Check: Feature-Matches zwischen zwei aufeinanderfolgenden
Aufnahmen (Frame_t-1 <-> Frame_t).

Zeichnet Verbindungslinien zwischen zueinander gehoerenden Merkmalen in zwei
Bildern (match_temporal_features()) -- fuer schnelles Nachvollziehen und als
Abbildung im Abschlussbericht.

Nutzung:
    python scripts/check_temporal_matches.py [--image-prev PATH] [--image-curr PATH]
                                              [--output PATH] [--ratio-threshold R]
                                              [--n-features N]

Ohne --image-prev/--image-curr: nutzt zwei verschiedene Stereo-Rohbilder aus
cal/bilder/ (lokale Ad-hoc-Testaufnahmen, gitignored, jeweils nur die linke
Haelfte -- simuliert "eine Kamera zu zwei Zeitpunkten"; die Aufnahmen zeigen
tatsaechlich dieselbe, unbewegte Kamera mit umpositioniertem Schachbrett, nicht
eine bewegte Kamera, dienen hier aber nur der Anschauung des Matching-
Mechanismus). Ohne verfuegbare Bilder: synthetisches Paar mit bekannter,
simulierter Verschiebung (np.roll).
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.localization.features import detect_features  # noqa: E402
from src.localization.temporal_matching import match_temporal_features  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "temporal_matches_demo.png"


def _find_demo_images() -> tuple[Path, Path] | None:
    """Sucht zwei verschiedene Stereo-Rohbilder in cal/bilder/."""
    demo_dir = REPO_ROOT / "cal" / "bilder"
    if not demo_dir.is_dir():
        return None
    candidates = sorted(demo_dir.glob("board_*raw.png"))
    if len(candidates) < 2:
        return None
    return candidates[0], candidates[-1]


def _left_half(combined: np.ndarray) -> np.ndarray:
    return combined[:, : combined.shape[1] // 2]


def _make_synthetic_frame_pair(size: int = 300, shift: tuple[int, int] = (15, 5)) -> tuple[np.ndarray, np.ndarray]:
    """Texturierte Szene, frame_curr = frame_prev um `shift` verschoben
    (simulierte Kamerabewegung) -- deterministisch (fester Seed)."""
    rng = np.random.default_rng(seed=42)
    frame_prev = np.full((size, size), 60, dtype=np.uint8)

    for _ in range(15):
        center = tuple(int(v) for v in rng.integers(40, size - 40, size=2))
        radius = int(rng.integers(8, 20))
        color = int(rng.integers(0, 255))
        cv2.circle(frame_prev, center, radius, color, thickness=-1)

    dx, dy = shift
    frame_curr = np.roll(frame_prev, (dy, dx), axis=(0, 1))
    return frame_prev, frame_curr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-prev", type=Path, default=None, help="Pfad zum Frame_t-1")
    parser.add_argument("--image-curr", type=Path, default=None, help="Pfad zum Frame_t")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Pfad fuer das annotierte Ausgabebild")
    parser.add_argument("--ratio-threshold", type=float, default=0.75, help="Lowe's-Ratio-Test-Schwellwert")
    parser.add_argument("--n-features", type=int, default=500, help="Max. Anzahl Merkmale (ORB nfeatures)")
    args = parser.parse_args()

    if args.image_prev is not None and args.image_curr is not None:
        image_paths = (args.image_prev, args.image_curr)
    else:
        image_paths = _find_demo_images()

    if image_paths is not None:
        path_prev, path_curr = image_paths
        raw_prev = cv2.imread(str(path_prev), cv2.IMREAD_GRAYSCALE)
        raw_curr = cv2.imread(str(path_curr), cv2.IMREAD_GRAYSCALE)
        if raw_prev is None or raw_curr is None:
            raise FileNotFoundError(f"Bild konnte nicht geladen werden: {path_prev} / {path_curr}")
        frame_prev, frame_curr = _left_half(raw_prev), _left_half(raw_curr)
        print(f"Verwende Bilder: {path_prev.name} (t-1) / {path_curr.name} (t), jeweils linke Haelfte")
        print("Hinweis: zeigt dieselbe, unbewegte Kamera mit umpositioniertem Schachbrett, nicht echte Kamerabewegung.")
    else:
        frame_prev, frame_curr = _make_synthetic_frame_pair()
        print("Keine Testbilder gefunden - verwende synthetisches Bildpaar (bekannte simulierte Verschiebung).")

    keypoints_prev, descriptors_prev = detect_features(frame_prev, n_features=args.n_features)
    keypoints_curr, descriptors_curr = detect_features(frame_curr, n_features=args.n_features)
    matches = match_temporal_features(descriptors_prev, descriptors_curr, ratio_threshold=args.ratio_threshold)

    print(f"{len(keypoints_prev)}/{len(keypoints_curr)} Merkmale in t-1/t, {len(matches)} gueltige Temporal-Matches.")

    annotated = cv2.drawMatches(
        frame_prev, keypoints_prev, frame_curr, keypoints_curr, matches, None,
        matchColor=(0, 255, 0), singlePointColor=(0, 0, 255),
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), annotated)
    print(f"Annotiertes Bild gespeichert: {args.output}")


if __name__ == "__main__":
    main()
