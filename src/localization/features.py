"""ORB feature detection on a single image.

Pure logic: operates on an already-loaded image array, no file or camera
I/O. Testable without a running camera (see tests/test_features.py).
"""

import cv2
import numpy as np


def detect_features(
    image: np.ndarray, n_features: int = 500
) -> tuple[tuple[cv2.KeyPoint, ...], np.ndarray]:
    """Detect ORB keypoints and their binary descriptors in an image.

    Args:
        image: grayscale or BGR image (BGR is converted internally).
        n_features: maximum number of keypoints to retain (ORB's
            `nfeatures`, keeps the strongest by response).

    Returns:
        keypoints: detected cv2.KeyPoint objects.
        descriptors: (N, 32) uint8 array, one row per keypoint. Empty
        (0, 32) array if no features were found.
    """
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(nfeatures=n_features)
    keypoints, descriptors = orb.detectAndCompute(image, None)

    if descriptors is None:
        descriptors = np.empty((0, 32), dtype=np.uint8)

    return keypoints, descriptors
