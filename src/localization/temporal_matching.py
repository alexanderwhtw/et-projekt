"""Temporal feature matching between consecutive frames (Frame_t-1 <-> Frame_t).

Pure logic: matches descriptors already detected by detect_features()
(typically the descriptors of the triangulated 3D points from
stereo_depth.triangulate_matches(), so a match's queryIdx/trainIdx also
index the corresponding 3D point arrays). No file or camera I/O.

Unlike stereo_depth.match_stereo_pairs(), there is no epipolar constraint
here (the camera moves freely between frames) -- ambiguous matches are
instead filtered with Lowe's ratio test.
"""

import cv2
import numpy as np


def match_temporal_features(
    descriptors_prev: np.ndarray,
    descriptors_curr: np.ndarray,
    ratio_threshold: float = 0.75,
) -> list[cv2.DMatch]:
    """Match ORB descriptors between two consecutive frames.

    Args:
        descriptors_prev: descriptors from detect_features() at Frame_t-1.
        descriptors_curr: descriptors from detect_features() at Frame_t.
        ratio_threshold: Lowe's ratio test threshold -- a match is kept only
            if the best candidate is closer than `ratio_threshold` times the
            second-best candidate (rejects ambiguous matches). Standard
            range 0.7-0.8.

    Returns:
        Matches (queryIdx into prev, trainIdx into curr), sorted by
        descriptor distance (best first).
    """
    if len(descriptors_prev) == 0 or len(descriptors_curr) == 0:
        return []

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn_matches = matcher.knnMatch(descriptors_prev, descriptors_curr, k=2)

    good = []
    for candidates in knn_matches:
        if len(candidates) < 2:
            continue
        best, second = candidates
        if best.distance < ratio_threshold * second.distance:
            good.append(best)

    good.sort(key=lambda m: m.distance)
    return good
