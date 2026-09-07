import numpy as np

from src.localization.temporal_matching import match_temporal_features


def _descriptor_with_distance(base: np.ndarray, distance: int) -> np.ndarray:
    """Copy of `base` with exactly the first `distance` bits flipped.

    Two descriptors built this way from the same base have Hamming distance
    |d1 - d2| from each other (the first min(d1,d2) flipped bits match, the
    rest differ) -- gives full control over Hamming distances in tests.
    """
    result = base.copy()
    for bit in range(distance):
        byte_idx, bit_idx = divmod(bit, 8)
        result[byte_idx] ^= 1 << bit_idx
    return result


def test_match_temporal_features_empty_descriptors():
    empty = np.empty((0, 32), dtype=np.uint8)
    assert match_temporal_features(empty, empty) == []


def test_match_temporal_features_ratio_test_rejects_ambiguous_matches():
    base = np.zeros(32, dtype=np.uint8)

    # query 0: two curr candidates almost equally close (distance 10 vs 11)
    #   -> ambiguous, ratio 10/11 ~ 0.91 > 0.75 -> rejected
    # query 1: one clearly best curr candidate (distance 0 vs next-best 39)
    #   -> unambiguous, ratio 0/39 ~ 0 -> accepted
    descriptors_prev = np.stack(
        [
            _descriptor_with_distance(base, 0),
            _descriptor_with_distance(base, 50),
        ]
    )
    descriptors_curr = np.stack(
        [
            _descriptor_with_distance(base, 10),
            _descriptor_with_distance(base, 11),
            _descriptor_with_distance(base, 50),
            _descriptor_with_distance(base, 90),
        ]
    )

    matches = match_temporal_features(descriptors_prev, descriptors_curr)

    assert len(matches) == 1
    assert matches[0].queryIdx == 1
    assert matches[0].trainIdx == 2


def test_match_temporal_features_ratio_threshold_relaxation_accepts_more():
    base = np.zeros(32, dtype=np.uint8)
    descriptors_prev = np.stack(
        [
            _descriptor_with_distance(base, 0),
            _descriptor_with_distance(base, 50),
        ]
    )
    descriptors_curr = np.stack(
        [
            _descriptor_with_distance(base, 10),
            _descriptor_with_distance(base, 11),
            _descriptor_with_distance(base, 50),
            _descriptor_with_distance(base, 90),
        ]
    )

    strict = match_temporal_features(descriptors_prev, descriptors_curr, ratio_threshold=0.75)
    relaxed = match_temporal_features(descriptors_prev, descriptors_curr, ratio_threshold=0.95)

    assert len(strict) == 1
    assert len(relaxed) == 2
