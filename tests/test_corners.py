import numpy as np

from src.calibration.corners import find_checkerboard_corners, generate_object_points

PATTERN_SIZE = (6, 7)  # matches the project's real board, see docs/decisions.md, 2026-09-04


def _make_checkerboard_image(pattern_size: tuple[int, int], square_px: int = 40, margin_px: int = 40) -> np.ndarray:
    cols, rows = pattern_size
    n_squares_x, n_squares_y = cols + 1, rows + 1
    width = n_squares_x * square_px + 2 * margin_px
    height = n_squares_y * square_px + 2 * margin_px
    image = np.full((height, width), 255, dtype=np.uint8)
    for row in range(n_squares_y):
        for col in range(n_squares_x):
            if (row + col) % 2 == 0:
                y0 = margin_px + row * square_px
                x0 = margin_px + col * square_px
                image[y0 : y0 + square_px, x0 : x0 + square_px] = 0
    return image


def test_find_checkerboard_corners_detects_known_pattern():
    image = _make_checkerboard_image(PATTERN_SIZE)

    corners = find_checkerboard_corners(image, PATTERN_SIZE)

    cols, rows = PATTERN_SIZE
    assert corners is not None
    assert corners.shape == (cols * rows, 2)
    # all corners should lie within the image bounds
    assert np.all(corners[:, 0] >= 0) and np.all(corners[:, 0] < image.shape[1])
    assert np.all(corners[:, 1] >= 0) and np.all(corners[:, 1] < image.shape[0])


def test_find_checkerboard_corners_detection_is_a_consistent_raster_grid():
    # detection order isn't guaranteed to start top-left/left-to-right (only
    # consistency across detections of the same physical board matters for
    # calibration, see corners.py docstring) -- verify it's a clean row-by-
    # row raster instead of asserting a specific starting corner/direction.
    square_px = 40
    image = _make_checkerboard_image(PATTERN_SIZE, square_px=square_px)
    cols, rows = PATTERN_SIZE

    corners = find_checkerboard_corners(image, PATTERN_SIZE).reshape(rows, cols, 2)

    within_row_step = corners[:, 1:] - corners[:, :-1]
    np.testing.assert_allclose(np.abs(within_row_step[:, :, 0]), square_px, atol=1.0)  # x steps by one square
    np.testing.assert_allclose(within_row_step[:, :, 1], 0.0, atol=1.0)  # same row -> constant y

    between_row_step = corners[1:, 0] - corners[:-1, 0]
    np.testing.assert_allclose(np.abs(between_row_step[:, 1]), square_px, atol=1.0)  # y steps by one square
    np.testing.assert_allclose(between_row_step[:, 0], 0.0, atol=1.0)  # first column -> constant x


def test_find_checkerboard_corners_returns_none_when_not_found():
    blank = np.full((300, 300), 128, dtype=np.uint8)
    assert find_checkerboard_corners(blank, PATTERN_SIZE) is None


def test_generate_object_points_shape_and_scale():
    square_size = 0.024  # 24mm, verified board square size, see docs/decisions.md, 2026-09-04
    cols, rows = PATTERN_SIZE

    points = generate_object_points(PATTERN_SIZE, square_size)

    assert points.shape == (cols * rows, 3)
    np.testing.assert_allclose(points[:, 2], 0.0)
    assert points[:, 0].max() == (cols - 1) * square_size
    assert points[:, 1].max() == (rows - 1) * square_size


def test_generate_object_points_is_a_consistent_raster_grid():
    square_size = 1.0
    cols, rows = PATTERN_SIZE

    points = generate_object_points(PATTERN_SIZE, square_size).reshape(rows, cols, 3)

    within_row_step = points[:, 1:] - points[:, :-1]
    expected_within_row = np.broadcast_to([square_size, 0, 0], within_row_step.shape)
    np.testing.assert_allclose(within_row_step, expected_within_row)

    between_row_step = points[1:, 0] - points[:-1, 0]
    expected_between_row = np.broadcast_to([0, square_size, 0], between_row_step.shape)
    np.testing.assert_allclose(between_row_step, expected_between_row)
