import numpy as np

from src.localization.features import detect_features


def _make_checkerboard(size: int = 200, square: int = 20) -> np.ndarray:
    """Synthetic grayscale checkerboard: deterministic, corner-rich."""
    board = np.zeros((size, size), dtype=np.uint8)
    for row in range(0, size, square):
        for col in range(0, size, square):
            if ((row // square) + (col // square)) % 2 == 0:
                board[row : row + square, col : col + square] = 255
    return board


def test_detect_features_finds_keypoints_on_checkerboard():
    image = _make_checkerboard()
    keypoints, descriptors = detect_features(image)

    assert len(keypoints) > 0
    assert descriptors.shape == (len(keypoints), 32)
    assert descriptors.dtype == np.uint8


def test_detect_features_returns_empty_on_blank_image():
    image = np.full((200, 200), 128, dtype=np.uint8)
    keypoints, descriptors = detect_features(image)

    assert len(keypoints) == 0
    assert descriptors.shape == (0, 32)


def test_detect_features_n_features_has_effect():
    # ORB's nfeatures is not a hard cap (on this symmetric checkerboard many
    # corners tie in response score, so a small budget still keeps several
    # of them) - assert the parameter measurably reduces the count instead
    # of assuming an exact limit.
    image = _make_checkerboard()
    keypoints_small, _ = detect_features(image, n_features=5)
    keypoints_large, _ = detect_features(image, n_features=500)

    assert len(keypoints_small) < len(keypoints_large)


def test_detect_features_accepts_bgr_input():
    gray = _make_checkerboard()
    bgr = np.stack([gray, gray, gray], axis=-1)

    kp_gray, _ = detect_features(gray)
    kp_bgr, _ = detect_features(bgr)

    assert len(kp_gray) == len(kp_bgr)
