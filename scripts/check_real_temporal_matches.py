"""Visueller Diagnose-Check: temporale Feature-Matches zwischen zwei echten,
rektifizierten Frames einer aufgenommenen Sequenz -- mit Tiefenfarbcodierung.

Anders als scripts/check_temporal_matches.py (generisches Demo, unrektifiziert
oder synthetisch) nutzt dieses Skript die ECHTE Kalibrierung + Rektifizierung
und exakt dieselben Pipeline-Bausteine wie run_vo_sequence.py
(extract_frame_points(), match_temporal_features()) -- zeigt also genau die
Korrespondenzen, die die VO-Pipeline fuer diesen Frame-Uebergang tatsaechlich
verwendet, samt ihrer triangulierten Tiefe (Z, Meter).

Grund: bei der Analyse von 2026-09-21_flur_route_v2 kam die Frage auf, ob ein
laengerer "eingefrorener" Trajektorien-Abschnitt (Frames ~34-50, kaum
Positionsaenderung trotz sichtbarer echter Kamerabewegung) durch Nah- oder
Fernbereichs-Tiefenfehler verursacht wird (siehe docs/decisions.md,
2026-09-21) -- eine Vermutung allein aus den Zahlen war nicht überzeugend,
daher dieses Skript zur direkten visuellen/quantitativen Pruefung.

Nutzung:
    python scripts/check_real_temporal_matches.py \
        --sequence-dir data/vo_sequences/2026-09-21_flur_route_v2 \
        --calibration results/calibration/2026-09-15_calibration.yaml \
        --frame-index 40 \
        [--output PATH]
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.io import load_calibration_result  # noqa: E402
from src.calibration.rectification import compute_rectification_maps  # noqa: E402
from src.localization.temporal_matching import match_temporal_features  # noqa: E402
from src.localization.vo_pipeline import extract_frame_points  # noqa: E402


def depth_color(z: float, near: float = 0.6, far: float = 1.5) -> tuple[int, int, int]:
    """Gruen (nah) -> Gelb -> Rot (fern), BGR fuer cv2."""
    t = np.clip((z - near) / (far - near), 0.0, 1.0)
    b = 0
    g = int(255 * (1 - t))
    r = int(255 * t)
    return (b, g, r)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sequence-dir", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--frame-index", type=int, required=True, help="t-1; vergleicht gegen Frame t = index+1")
    parser.add_argument("--output", type=Path, default=None, help="Default: scripts/output/real_temporal_matches_<idx>.png")
    args = parser.parse_args()

    calib = load_calibration_result(args.calibration)
    image_size = calib["image_size"]
    map_x_L, map_y_L = compute_rectification_maps(
        calib["left"]["K"], calib["left"]["dist"], calib["rectification"]["R1"], calib["rectification"]["P1"], image_size
    )
    map_x_R, map_y_R = compute_rectification_maps(
        calib["right"]["K"], calib["right"]["dist"], calib["rectification"]["R2"], calib["rectification"]["P2"], image_size
    )
    P_L, P_R = calib["rectification"]["P1"], calib["rectification"]["P2"]

    def load_rectified(idx: int) -> tuple[np.ndarray, np.ndarray]:
        left = cv2.imread(str(args.sequence_dir / f"left_{idx:03d}.png"), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(args.sequence_dir / f"right_{idx:03d}.png"), cv2.IMREAD_GRAYSCALE)
        left_rect = cv2.remap(left, map_x_L, map_y_L, cv2.INTER_LINEAR)
        right_rect = cv2.remap(right, map_x_R, map_y_R, cv2.INTER_LINEAR)
        return left_rect, right_rect

    i = args.frame_index
    image_L_prev, image_R_prev = load_rectified(i)
    image_L_curr, image_R_curr = load_rectified(i + 1)

    points_prev, descriptors_prev = extract_frame_points(image_L_prev, image_R_prev, P_L, P_R)
    points_curr, descriptors_curr = extract_frame_points(image_L_curr, image_R_curr, P_L, P_R)

    # re-detect keypoints (pixel positions) for drawing -- extract_frame_points()
    # only returns 3D points + descriptors, not the 2D keypoint objects
    from src.localization.features import detect_features
    from src.localization.stereo_depth import match_stereo_pairs

    kp_L_prev, desc_L_prev = detect_features(image_L_prev)
    kp_R_prev, desc_R_prev = detect_features(image_R_prev)
    stereo_matches_prev = match_stereo_pairs(kp_L_prev, desc_L_prev, kp_R_prev, desc_R_prev)
    kp_L_curr, desc_L_curr = detect_features(image_L_curr)
    kp_R_curr, desc_R_curr = detect_features(image_R_curr)
    stereo_matches_curr = match_stereo_pairs(kp_L_curr, desc_L_curr, kp_R_curr, desc_R_curr)

    pts2d_prev = [kp_L_prev[m.queryIdx].pt for m in stereo_matches_prev]
    pts2d_curr = [kp_L_curr[m.queryIdx].pt for m in stereo_matches_curr]

    temporal_matches = match_temporal_features(descriptors_prev, descriptors_curr)
    print(f"Frame {i} -> {i + 1}: {len(points_prev)}/{len(points_curr)} triangulierte Punkte, "
          f"{len(temporal_matches)} temporale Matches.")

    depths = [points_prev[m.queryIdx][2] for m in temporal_matches]
    if depths:
        print(f"Tiefe der gematchten Punkte (Frame {i}): min={min(depths):.2f}m  "
              f"median={np.median(depths):.2f}m  max={max(depths):.2f}m")
        print("Zielbereich laut CLAUDE.md: 0.3-2.0m")
        n_near = sum(1 for d in depths if d < 0.3)
        n_far = sum(1 for d in depths if d > 2.0)
        print(f"  Punkte < 0.3m (Nahbereich-Verletzung): {n_near}/{len(depths)}")
        print(f"  Punkte > 2.0m (Fernbereich-Verletzung): {n_far}/{len(depths)}")

    canvas = cv2.cvtColor(np.hstack([image_L_prev, image_L_curr]), cv2.COLOR_GRAY2BGR)
    offset = image_L_prev.shape[1]
    for m in temporal_matches:
        z = points_prev[m.queryIdx][2]
        color = depth_color(z)
        x_prev, y_prev = (int(v) for v in pts2d_prev[m.queryIdx])
        x_curr, y_curr = (int(v) for v in pts2d_curr[m.trainIdx])
        cv2.circle(canvas, (x_prev, y_prev), 5, color, 2)
        cv2.circle(canvas, (x_curr + offset, y_curr), 5, color, 2)
        cv2.line(canvas, (x_prev, y_prev), (x_curr + offset, y_curr), color, 1)
        cv2.putText(canvas, f"{z:.2f}", (x_prev + 6, y_prev - 6), cv2.FONT_HERSHEY_PLAIN, 0.9, color, 1)

    cv2.putText(canvas, f"Frame {i}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(canvas, f"Frame {i + 1}", (offset + 10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(canvas, "Farbe: gruen=nah, rot=fern (Zahl=Tiefe in m)", (10, image_L_prev.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    output = args.output or REPO_ROOT / "scripts" / "output" / f"real_temporal_matches_{i:03d}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    print(f"Annotiertes Bild gespeichert: {output}")


if __name__ == "__main__":
    main()
