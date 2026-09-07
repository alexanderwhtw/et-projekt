"""Visueller Sanity-Check: Reprojection-Error-Plot der Kalibrierung.

Zeigt den Reprojection-Error pro Kalibrierbild als Balkendiagramm -- die
Kennzahl allein (RMS ueber alle Bilder) verdeckt einzelne schlechte
Aufnahmen (z.B. Board leicht bewegt waehrend der Aufnahme, Ecken falsch
erkannt); der Plot macht sie sichtbar.

Nutzung:
    python scripts/check_calibration.py [--output PATH] [--cols N] [--rows N]
                                         [--square-size M] [--threshold-px PX]

Ohne echte Kalibrierbilder (data/calibration_images/ ist noch leer, Phase 1
Datenaufnahme steht noch aus) verwendet dieses Skript ein synthetisches
Kalibrier-Set (bekannte Kamera, bekannte Boardposen) mit realistischem
Subpixel-Rauschen auf allen Bildern und einem absichtlich staerker
gestoerten Bild -- demonstriert, dass der Plot ein schlechtes Bild
tatsaechlich sichtbar macht.
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

from src.calibration.corners import generate_object_points  # noqa: E402
from src.calibration.intrinsics import calibrate_intrinsics, compute_per_image_reprojection_errors  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "calibration_reprojection_error.png"


def _make_synthetic_calibration_set(
    pattern_size: tuple[int, int], square_size: float, image_size: tuple[int, int], n_images: int = 12, seed: int = 0
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    true_K = np.array([[500.0, 0, image_size[0] / 2], [0, 500.0, image_size[1] / 2], [0, 0, 1.0]])
    true_dist = np.array([-0.1, 0.03, 0.0, 0.0, 0.0])
    object_points = generate_object_points(pattern_size, square_size)
    rng = np.random.default_rng(seed)

    object_points_list, image_points_list = [], []
    for i in range(n_images):
        rvec = rng.uniform(-0.4, 0.4, size=3)
        tvec = np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.1, 0.1), rng.uniform(0.6, 1.4)])
        projected, _ = cv2.projectPoints(object_points, rvec, tvec, true_K, true_dist)
        points = projected.reshape(-1, 2)

        noise_std = 0.3 if i != n_images - 1 else 2.5  # letztes Bild absichtlich schlechter
        points = points + rng.normal(scale=noise_std, size=points.shape)

        image_points_list.append(points.astype(np.float32))
        object_points_list.append(object_points)

    return object_points_list, image_points_list


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--rows", type=int, default=7)
    parser.add_argument("--square-size", type=float, default=0.024, help="Kantenlaenge eines Feldes (m)")
    parser.add_argument("--threshold-px", type=float, default=1.0, help="Warnschwelle pro Bild (px)")
    args = parser.parse_args()
    pattern_size = (args.cols, args.rows)
    image_size = (640, 480)

    # TODO: echte Bilder aus data/calibration_images/ + manifest.csv laden,
    # sobald die Kalibrier-Datenaufnahme (Phase 1) stattgefunden hat.
    object_points_list, image_points_list = _make_synthetic_calibration_set(pattern_size, args.square_size, image_size)
    print(f"Synthetisches Kalibrier-Set verwendet ({len(object_points_list)} Bilder) - noch keine echten Kalibrierbilder vorhanden.")

    K, dist, overall_error = calibrate_intrinsics(object_points_list, image_points_list, image_size)
    per_image_errors = compute_per_image_reprojection_errors(object_points_list, image_points_list, K, dist)

    print(f"Gesamt-RMS-Reprojection-Error: {overall_error:.3f}px")
    for i, err in enumerate(per_image_errors):
        flag = " <-- ueber Schwelle" if err > args.threshold_px else ""
        print(f"  Bild {i}: {err:.3f}px{flag}")

    colors = ["tab:red" if e > args.threshold_px else "tab:blue" for e in per_image_errors]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(len(per_image_errors)), per_image_errors, color=colors)
    ax.axhline(overall_error, color="gray", linestyle="--", label=f"Gesamt-RMS ({overall_error:.2f}px)")
    ax.axhline(args.threshold_px, color="red", linestyle=":", label=f"Schwelle ({args.threshold_px}px)")
    ax.set_xlabel("Kalibrierbild")
    ax.set_ylabel("RMS Reprojection Error (px)")
    ax.set_title("Reprojection Error pro Kalibrierbild")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    print(f"Plot gespeichert: {args.output}")


if __name__ == "__main__":
    main()
