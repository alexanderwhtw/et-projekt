"""Visueller Sanity-Check: rektifizierte Stereo-Bilder mit horizontalen
Referenzlinien (muessen sich links/rechts decken).

Baut eine synthetische 3D-Szene, rendert sie ueber ein bekanntes, verzeichnetes
Stereo-Kameramodell (K, dist, R, T -- inkl. einer Roll-Verkippung wie beim
aktuellen unkalibrierten Rig, siehe docs/decisions.md, 2026-09-02) zu zwei
Rohbildern, rektifiziert beide (compute_rectification() + cv2.remap) und
zeichnet horizontale Referenzlinien ein. Nach korrekter Rektifizierung muss
derselbe Szenepunkt in beiden Bildern auf derselben Linie liegen.

Nutzung:
    python scripts/check_rectification.py [--output PATH] [--n-points N]
                                           [--alpha A]

Echte Kalibrierbilder liegen noch nicht vor (Phase 1 Datenaufnahme steht
aus) -- die verwendeten K/dist/R/T sind ein plausibles, aber synthetisches
Platzhalter-Kameramodell.
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.rectification import compute_rectification, compute_rectification_maps  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "output" / "rectification_demo.png"
IMAGE_SIZE = (640, 480)  # (width, height)
BASELINE = 0.06  # reale Arducam B0266 Baseline, siehe docs/decisions.md, 2026-09-02


def _synthetic_stereo_rig():
    K_L = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
    K_R = np.array([[505.0, 0, 315.0], [0, 505.0, 245.0], [0, 0, 1.0]])
    dist_L = np.array([-0.15, 0.05, 0.0, 0.0, 0.0])
    dist_R = np.array([-0.13, 0.04, 0.0, 0.0, 0.0])
    # Roll-Verkippung wie beim aktuellen unrektifizierten Rig (~2.25 deg),
    # siehe docs/decisions.md, 2026-09-02
    R = cv2.Rodrigues(np.array([0.0, 0.0, np.radians(2.25)]))[0]
    T = np.array([BASELINE, 0.0, 0.0])
    return K_L, dist_L, K_R, dist_R, R, T


def _render_scene(points_3d: np.ndarray, K: np.ndarray, dist: np.ndarray, rvec: np.ndarray, tvec: np.ndarray) -> np.ndarray:
    width, height = IMAGE_SIZE
    image = np.full((height, width), 40, dtype=np.uint8)
    projected, _ = cv2.projectPoints(points_3d, rvec, tvec, K, dist)
    for i, (x, y) in enumerate(projected.reshape(-1, 2)):
        if 0 <= x < width and 0 <= y < height:
            color = int(80 + 175 * (i % 5) / 4)
            cv2.circle(image, (int(round(x)), int(round(y))), 10, color, thickness=-1)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-points", type=int, default=25)
    parser.add_argument("--alpha", type=float, default=0.0, help="0=nur gueltige Pixel, 1=alle Pixel (schwarze Raender)")
    args = parser.parse_args()

    K_L, dist_L, K_R, dist_R, R, T = _synthetic_stereo_rig()

    rng = np.random.default_rng(0)
    xy = rng.uniform(-0.4, 0.4, size=(args.n_points, 2))
    z = rng.uniform(0.4, 1.8, size=(args.n_points, 1))
    points_3d = np.hstack([xy, z])

    rvec_R, _ = cv2.Rodrigues(R)
    raw_L = _render_scene(points_3d, K_L, dist_L, np.zeros(3), np.zeros(3))
    raw_R = _render_scene(points_3d, K_R, dist_R, rvec_R.flatten(), T)

    R1, R2, P1, P2, _Q = compute_rectification(K_L, dist_L, K_R, dist_R, IMAGE_SIZE, R, T, alpha=args.alpha)
    map_L = compute_rectification_maps(K_L, dist_L, R1, P1, IMAGE_SIZE)
    map_R = compute_rectification_maps(K_R, dist_R, R2, P2, IMAGE_SIZE)

    rect_L = cv2.remap(raw_L, *map_L, cv2.INTER_LINEAR)
    rect_R = cv2.remap(raw_R, *map_R, cv2.INTER_LINEAR)

    # quantitativer Check: liegt derselbe Szenepunkt in L/R auf derselben Zeile?
    max_row_deviation = 0.0
    for point in points_3d:
        point_h = np.append(point, 1.0)
        y_L = (P1 @ point_h)[1] / (P1 @ point_h)[2]
        y_R = (P2 @ point_h)[1] / (P2 @ point_h)[2]
        max_row_deviation = max(max_row_deviation, abs(y_L - y_R))
    print(f"Max. Zeilenabweichung zwischen L/R (aus P1/P2, sollte ~0 sein): {max_row_deviation:.2e}px")

    combined = cv2.cvtColor(np.hstack([rect_L, rect_R]), cv2.COLOR_GRAY2BGR)
    width = rect_L.shape[1]
    for y in range(0, combined.shape[0], 40):
        cv2.line(combined, (0, y), (combined.shape[1], y), (0, 255, 0), 1)
    cv2.line(combined, (width, 0), (width, combined.shape[0]), (255, 0, 0), 2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), combined)
    print(f"Rektifizierte Bilder (L | R) mit Referenzlinien gespeichert: {args.output}")


if __name__ == "__main__":
    main()
