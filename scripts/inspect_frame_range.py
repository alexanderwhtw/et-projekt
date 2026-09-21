"""Diagnose-Tool: laeuft ueber einen Frame-Bereich einer Sequenz und druckt
pro Frame-Uebergang Match-Anzahl, Tiefenstatistik der gematchten Punkte und
die tatsaechlich geschaetzte Relativ-Pose -- fuer die systematische
Fehlersuche in einem laengeren "verdaechtigen" Abschnitt (z.B. ein
Trajektorien-Abschnitt ohne erkennbaren Fortschritt trotz realer Bewegung),
siehe docs/decisions.md, 2026-09-21.

Nutzt exakt dieselben Pipeline-Bausteine wie run_vo_sequence.py
(extract_frame_points(), match_temporal_features(), estimate_relative_pose_ransac()),
mit festem Seed fuer Reproduzierbarkeit -- kein Ersatz fuer run_vo_sequence.py,
sondern ein Blick INS Detail eines einzelnen Bereichs.

Nutzung:
    python scripts/inspect_frame_range.py \
        --sequence-dir data/vo_sequences/2026-09-21_flur_route_v2 \
        --calibration results/calibration/2026-09-15_calibration.yaml \
        --start 25 --end 55
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
from src.localization.pose_estimation import estimate_relative_pose_ransac  # noqa: E402
from src.localization.temporal_matching import match_temporal_features  # noqa: E402
from src.localization.vo_pipeline import extract_frame_points  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sequence-dir", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
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

    points_prev, descriptors_prev = extract_frame_points(*load_rectified(args.start), P_L, P_R)
    print(f"Frame {args.start}: {len(points_prev)} triangulierte Punkte")
    print(f"{'Uebergang':>12} {'n_pts':>6} {'n_match':>8} {'inliers':>8} {'depth_med':>10} {'depth_far%':>11} "
          f"{'t_x':>7} {'t_y':>7} {'t_z':>7} {'|t|':>7}")

    for i in range(args.start, args.end):
        points_curr, descriptors_curr = extract_frame_points(*load_rectified(i + 1), P_L, P_R)
        matches = match_temporal_features(descriptors_prev, descriptors_curr)

        if len(matches) < 3:
            print(f"{i:>4}->{i + 1:<4}   {len(points_prev):>6} {len(matches):>8}  -- zu wenige Matches --")
            points_prev, descriptors_prev = points_curr, descriptors_curr
            continue

        depths = np.array([points_prev[m.queryIdx][2] for m in matches])
        matched_prev = points_prev[[m.queryIdx for m in matches]]
        matched_curr = points_curr[[m.trainIdx for m in matches]]
        try:
            R, t, inlier_mask = estimate_relative_pose_ransac(matched_prev, matched_curr, seed=args.seed)
            n_inliers = int(inlier_mask.sum())
            depth_med_inliers = np.median(depths[inlier_mask])
            far_pct_inliers = 100 * np.mean(depths[inlier_mask] > 2.0)
            t_str = f"{t[0]:+7.3f} {t[1]:+7.3f} {t[2]:+7.3f} {np.linalg.norm(t):7.3f}"
        except RuntimeError as e:
            n_inliers = 0
            depth_med_inliers = np.median(depths)
            far_pct_inliers = 100 * np.mean(depths > 2.0)
            t_str = f"   FEHLER: {e}"

        print(f"{i:>4}->{i + 1:<4}   {len(points_prev):>6} {len(matches):>8} {n_inliers:>8} "
              f"{depth_med_inliers:>10.2f} {far_pct_inliers:>10.1f}% {t_str}")

        points_prev, descriptors_prev = points_curr, descriptors_curr


if __name__ == "__main__":
    main()
