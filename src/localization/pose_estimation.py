"""Relative camera motion from matched 3D-3D point correspondences.

Pure logic: rigid registration (Kabsch/Umeyama algorithm) between two
index-aligned 3D point sets. No file or camera I/O.

Convention: points_prev/points_curr are the triangulated 3D points
(stereo_depth.triangulate_matches()) of the same physical points, expressed
in each frame's own camera coordinate frame, matched via
temporal_matching.match_temporal_features(). The estimated (R, t) maps
points_curr into the points_prev frame -- i.e. it is the pose of the camera
at Frame_t expressed in the Frame_t-1 camera frame, exactly the
Delta-Pose in `Pose_t = Pose_t-1 . Delta-Pose` used for trajectory chaining
(see docs/decisions.md, 2026-09-04).
"""

import cv2
import numpy as np


class ImplausiblePoseError(RuntimeError):
    """A relative pose was estimated (RANSAC found enough inliers), but its
    magnitude exceeds a physically reasoned per-step motion bound (see
    check_pose_plausibility(), docs/decisions.md 2026-09-21). Unlike the
    plain RuntimeError above (too few inliers -- no usable pose exists at
    all), a full previous VO state remains valid here, so callers can skip
    this one frame and retry with the next one instead of stopping the
    trajectory for good."""


def relative_pose_magnitude(R: np.ndarray, t: np.ndarray) -> tuple[float, float]:
    """Translation distance (m) and rotation angle (deg) of a relative pose."""
    translation_m = float(np.linalg.norm(t))
    rvec, _ = cv2.Rodrigues(R)
    rotation_deg = float(np.degrees(np.linalg.norm(rvec)))
    return translation_m, rotation_deg


def check_pose_plausibility(
    R: np.ndarray,
    t: np.ndarray,
    max_translation_m: float | None,
    max_rotation_deg: float | None,
) -> None:
    """Raise ImplausiblePoseError if (R, t) exceeds a physically reasoned
    per-step motion bound. Either bound is disabled by passing None.

    Motivation (see docs/decisions.md, 2026-09-21): real captured sequences
    showed isolated frame-to-frame mismatches at repetitive scene structures
    (door frame edges, a checkered curtain, a ladder's evenly spaced rungs)
    that RANSAC accepted as self-consistent (the wrong correspondences agree
    with each other), producing single-step jumps of ~0.3-0.4m against a
    background distribution with median ~0.03m and 95th percentile ~0.18m --
    clearly separated from normal motion, not just noisy. RANSAC's inlier
    count alone cannot distinguish "self-consistently wrong" from "correct";
    an independent physical plausibility bound can.
    """
    translation_m, rotation_deg = relative_pose_magnitude(R, t)
    if max_translation_m is not None and translation_m > max_translation_m:
        raise ImplausiblePoseError(
            f"translation {translation_m:.3f}m exceeds max_translation_m={max_translation_m}"
        )
    if max_rotation_deg is not None and rotation_deg > max_rotation_deg:
        raise ImplausiblePoseError(f"rotation {rotation_deg:.1f}deg exceeds max_rotation_deg={max_rotation_deg}")


def estimate_relative_pose(
    points_prev: np.ndarray,
    points_curr: np.ndarray,
    weights: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate the rigid transform mapping points_curr onto points_prev.

    Args:
        points_prev: (N, 3) 3D points in the Frame_t-1 camera frame.
        points_curr: (N, 3) the same physical points (index-aligned
            correspondences), in the Frame_t camera frame. N >= 3,
            not all collinear.
        weights: optional (N,) per-correspondence weights (see
            depth_weights()). None (default) weights every correspondence
            equally -- identical result to the original unweighted Kabsch
            fit, since uniform weights only rescale H by a constant factor
            and leave its SVD's singular vectors unchanged.

    Returns:
        R: (3, 3) rotation matrix.
        t: (3,) translation vector.
        Such that points_prev[i] ~= R @ points_curr[i] + t (weighted
        least-squares, Kabsch/Umeyama algorithm).
    """
    points_prev = np.asarray(points_prev, dtype=np.float64)
    points_curr = np.asarray(points_curr, dtype=np.float64)

    if points_prev.shape != points_curr.shape:
        raise ValueError(f"shape mismatch: {points_prev.shape} vs {points_curr.shape}")
    if points_prev.shape[0] < 3:
        raise ValueError(f"need at least 3 point correspondences, got {points_prev.shape[0]}")

    n = points_prev.shape[0]
    if weights is None:
        w = np.full(n, 1.0 / n)
    else:
        w = np.asarray(weights, dtype=np.float64)
        if w.shape != (n,):
            raise ValueError(f"weights shape {w.shape} does not match {n} points")
        w = w / w.sum()

    centroid_prev = w @ points_prev
    centroid_curr = w @ points_curr
    prev_centered = points_prev - centroid_prev
    curr_centered = points_curr - centroid_curr

    H = (curr_centered * w[:, None]).T @ prev_centered
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    t = centroid_prev - R @ centroid_curr

    return R, t


def depth_weights(points_prev: np.ndarray, points_curr: np.ndarray, power: float = 4.0) -> np.ndarray:
    """Per-correspondence weights for estimate_relative_pose(), down-weighting
    points whose triangulated depth makes them positionally unreliable.

    Motivation (see docs/decisions.md, 2026-09-21 Teil 5/7 and 2026-09-23):
    for a fixed stereo baseline, depth error grows quadratically with
    distance, Delta_Z = Z^2 * Delta_d / (f*B) -- so a far point's positional
    noise VARIANCE grows as Z^4 (power=4 matches this directly: the
    statistically motivated inverse-variance weight for a weighted least-
    squares fit). A correspondence's total noise reflects both frames it was
    triangulated in, so the two points' Z^power are combined. This is the
    "gewichtete Kabsch/Procrustes-Anpassung" floated in Teil 7 -- it targets
    failure mode 4 (Fernbereichs-"Einfrieren": distant, noisy points
    systematically dragging the fit toward too little motion), not failure
    mode 5 (geometric degeneracy from spatially clustered inliers, which is
    independent of depth accuracy and unaffected by this weighting).

    Args:
        points_prev, points_curr: (N, 3) triangulated points, camera-frame Z
            (third column) is the relevant depth.
        power: exponent applied to depth before inverting (default 4.0, see
            above). Exposed for the sensitivity check this project's
            convention requires (docs/decisions.md, 2026-09-21 Teil 4) --
            e.g. power=2.0 weights by inverse depth-noise-STD instead of
            inverse variance, a gentler down-weighting.

    Returns:
        (N,) weights, NOT normalized (estimate_relative_pose() normalizes
        internally). Depth is clamped to a small positive epsilon to avoid
        division by zero for degenerate (non-positive) triangulated depth.
    """
    z_prev = np.clip(np.asarray(points_prev, dtype=np.float64)[:, 2], 1e-6, None)
    z_curr = np.clip(np.asarray(points_curr, dtype=np.float64)[:, 2], 1e-6, None)
    return 1.0 / (z_prev**power + z_curr**power)


def estimate_relative_pose_ransac(
    points_prev: np.ndarray,
    points_curr: np.ndarray,
    inlier_threshold: float = 0.02,
    max_iterations: int = 200,
    seed: int | None = None,
    use_depth_weighting: bool = False,
    depth_weight_power: float = 4.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Robust version of estimate_relative_pose() using RANSAC.

    Feature matching (stereo and temporal) reliably produces a fraction of
    wrong correspondences even on well-behaved input -- diagnosed empirically
    while building vo_pipeline.py (see docs/decisions.md, 2026-09-07): ~15%
    wrong disparities already at the stereo-matching stage, compounding to
    ~39% outliers in the final temporal correspondences on a synthetic test
    scene. Plain estimate_relative_pose() (least-squares Kabsch) has no
    protection against this. RANSAC repeatedly fits a minimal 3-point Kabsch
    hypothesis, counts inliers under `inlier_threshold`, and refits on the
    largest inlier set found.

    Args:
        points_prev, points_curr: see estimate_relative_pose(). N >= 3.
        inlier_threshold: max residual (m) after applying a hypothesis for a
            correspondence to count as an inlier. Default 0.02m (2cm) is a
            starting point for the project's 0.3-2m target range (see
            CLAUDE.md), not yet validated against real measurements.
        max_iterations: number of random 3-point hypotheses to try.
        seed: RNG seed for reproducible sampling (tests); None = nondeterministic.
        use_depth_weighting: if True, the FINAL refit on the winning inlier
            set uses depth_weights() instead of a plain unweighted Kabsch
            fit (see docs/decisions.md, 2026-09-23). Only the refit is
            affected -- hypothesis generation and inlier counting stay
            unweighted/unchanged, since that consensus step is already
            validated (2026-09-21 sensitivity check) and not what the depth-
            weighting idea targets. Default False preserves prior behaviour
            exactly.
        depth_weight_power: forwarded to depth_weights() when
            use_depth_weighting is True.

    Returns:
        R, t: refit via estimate_relative_pose() on the largest inlier set.
        inlier_mask: (N,) bool array, True for correspondences used in the
            final refit.

    Raises:
        RuntimeError: even the best 3-point hypothesis found fewer than 3
            inliers (including, potentially, some of its own 3 sample
            points -- a 3-point Kabsch fit is only exact for noiseless,
            perfectly consistent correspondences; real triangulated points
            carry noise, so a tight inlier_threshold can reject even the
            fitted points themselves). Observed live on 2026-09-17 with
            noisier images (reduced exposure + higher gain, see
            docs/decisions.md) -- previously an uncaught ValueError from
            the refit call below, crashing the live-VO loop instead of
            being handled like the "too few temporal matches" case.
    """
    points_prev = np.asarray(points_prev, dtype=np.float64)
    points_curr = np.asarray(points_curr, dtype=np.float64)

    if points_prev.shape[0] < 3:
        raise ValueError(f"need at least 3 point correspondences, got {points_prev.shape[0]}")

    rng = np.random.default_rng(seed)
    n = points_prev.shape[0]

    best_inlier_mask = None
    best_inlier_count = -1

    for _ in range(max_iterations):
        sample_idx = rng.choice(n, size=3, replace=False)
        R, t = estimate_relative_pose(points_prev[sample_idx], points_curr[sample_idx])

        residuals = np.linalg.norm(points_prev - (points_curr @ R.T + t), axis=1)
        inlier_mask = residuals < inlier_threshold
        inlier_count = int(inlier_mask.sum())

        if inlier_count > best_inlier_count:
            best_inlier_count = inlier_count
            best_inlier_mask = inlier_mask

    if best_inlier_count < 3:
        raise RuntimeError(
            f"RANSAC found only {best_inlier_count} inliers (< 3) over {max_iterations} iterations "
            "-- cannot fit a rigid pose, correspondences too noisy/inconsistent"
        )
    inlier_prev = points_prev[best_inlier_mask]
    inlier_curr = points_curr[best_inlier_mask]
    weights = depth_weights(inlier_prev, inlier_curr, depth_weight_power) if use_depth_weighting else None
    R, t = estimate_relative_pose(inlier_prev, inlier_curr, weights)
    return R, t, best_inlier_mask
