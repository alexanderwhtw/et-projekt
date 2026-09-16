"""Visueller Sanity-Check: dichte Disparitätskarte eines rektifizierten
Stereo-Paars (compute_disparity_map(), cv2.StereoSGBM).

Rein illustrativ fuer den Abschlussbericht -- die VO-Pipeline nutzt sparse
ORB-Merkmale + Stereo-Matching (match_stereo_pairs()/triangulate_matches()
in src/localization/stereo_depth.py), nicht diese dichte Karte. War der
letzte offene Sanity-Check-Stub aus CLAUDE.md, siehe docs/decisions.md
(2026-09-16).

Nutzung:
    python scripts/check_disparity.py [--left PATH --right PATH] [--output PATH]
                                       [--num-disparities N] [--block-size N]

Ohne --left/--right: nutzt das juengste rektifizierte Bildpaar aus
results/measurements/*_depth_validation_*/ (echte Kamerabilder), oder
generiert sonst ein synthetisches Stereo-Paar mit bekannter Disparitaet.
"""

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.localization.stereo_depth import compute_disparity_map  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "disparity_demo.png"


def _find_demo_pair() -> tuple[Path, Path] | None:
    """Sucht das juengste rektifizierte Bildpaar in results/measurements/*_depth_validation_*/."""
    candidates = sorted((REPO_ROOT / "results" / "measurements").glob("*_depth_validation_*"))
    for directory in reversed(candidates):
        left, right = directory / "left_rectified.png", directory / "right_rectified.png"
        if left.exists() and right.exists():
            return left, right
    return None


def _make_synthetic_stereo_pair(size: int = 400, disparity: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Texturierte Szene mit bekannter, konstanter Disparitaet (fronto-
    parallele Ebene) -- deterministisch (fester Seed)."""
    rng = np.random.default_rng(seed=42)
    left = np.full((size, size), 60, dtype=np.uint8)
    for _ in range(40):
        center = tuple(int(v) for v in rng.integers(40, size - 40, size=2))
        radius = int(rng.integers(6, 18))
        color = int(rng.integers(0, 255))
        cv2.circle(left, center, radius, color, thickness=-1)
    right = np.roll(left, -disparity, axis=1)
    return left, right


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--left", type=Path, default=None, help="Pfad zum rektifizierten linken Bild")
    parser.add_argument("--right", type=Path, default=None, help="Pfad zum rektifizierten rechten Bild")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--num-disparities", type=int, default=64, help="Max. Suchbereich (px), Vielfaches von 16")
    parser.add_argument("--block-size", type=int, default=9, help="Block-Groesse (ungerade, >=3)")
    args = parser.parse_args()

    if args.left is not None and args.right is not None:
        left_path, right_path = args.left, args.right
    else:
        demo_pair = _find_demo_pair()
        left_path, right_path = demo_pair if demo_pair else (None, None)

    if left_path is not None:
        left = cv2.imread(str(left_path), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(right_path), cv2.IMREAD_GRAYSCALE)
        if left is None or right is None:
            raise FileNotFoundError(f"Bild konnte nicht geladen werden: {left_path} / {right_path}")
        print(f"Verwende rektifiziertes Bildpaar: {left_path.parent}")
    else:
        left, right = _make_synthetic_stereo_pair()
        print("Kein rektifiziertes Bildpaar gefunden - verwende synthetisches Demo-Paar (bekannte Disparitaet=20px).")

    disparity = compute_disparity_map(left, right, args.num_disparities, args.block_size)

    valid = disparity[~np.isnan(disparity)]
    coverage_pct = 100 * valid.size / disparity.size
    print(
        f"Disparitaet: {coverage_pct:.1f}% gueltige Pixel, "
        f"Median={np.nanmedian(disparity):.1f}px, Min={valid.min():.1f}px, Max={valid.max():.1f}px"
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].imshow(left, cmap="gray")
    axes[0].set_title("Linkes Bild (rektifiziert)")
    axes[0].axis("off")

    im = axes[1].imshow(disparity, cmap="turbo")
    axes[1].set_title("Disparitätskarte (px)")
    axes[1].axis("off")
    fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04, label="Disparität (px)")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150, bbox_inches="tight")
    print(f"Plot gespeichert: {args.output}")


if __name__ == "__main__":
    main()
