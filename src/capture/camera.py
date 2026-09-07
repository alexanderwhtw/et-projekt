"""Camera I/O: trigger stereo still captures via rpicam-still.

The Arducam B0266 stereo kit exposes both cameras as a single
`arducam-pivariety` device -- one rpicam-still call returns one combined
2560x800 frame (left in columns 0-1279, right in 1280-2559), no manual
multi-camera synchronization needed (see docs/decisions.md, 2026-09-02).

Raspberry-Pi-only: capture_frame() needs rpicam-still and the actual
camera hardware, so it cannot be exercised on a dev machine without the
Pi -- see tests/test_camera.py, which mocks subprocess.run instead.
"""

import subprocess
from pathlib import Path

import numpy as np

DEFAULT_WIDTH = 2560
DEFAULT_HEIGHT = 800
DEFAULT_TIMEOUT_MS = 300


def build_capture_command(
    output_path: Path,
    shutter_us: int,
    gain: float,
    awb_gains: tuple[float, float] = (1.0, 1.0),
    denoise: str = "off",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> list[str]:
    """Build the rpicam-still command line for one stereo still capture.

    Settings convention established in docs/decisions.md (2026-09-02,
    2026-09-03): manual exposure/gain (auto-exposure would drift between
    calibration frames), AWB fixed at (1,1) (mono sensor, AWB irrelevant),
    denoise off (would smooth checkerboard corners). Lighting is not stable
    between sessions -- shutter/gain must be re-checked each time, not
    hardcoded (see docs/decisions.md, 2026-09-03).

    Returns:
        Argument list for subprocess.run(), e.g.
        ["rpicam-still", "-n", "-t", "300", "--shutter", "3500", ...].
    """
    return [
        "rpicam-still",
        "-n",
        "-t", str(timeout_ms),
        "--shutter", str(shutter_us),
        "--gain", str(gain),
        "--awbgains", f"{awb_gains[0]},{awb_gains[1]}",
        "--denoise", denoise,
        "--width", str(width),
        "--height", str(height),
        "--encoding", "png",
        "-o", str(output_path),
    ]


def capture_frame(
    output_path: Path,
    shutter_us: int,
    gain: float,
    awb_gains: tuple[float, float] = (1.0, 1.0),
    denoise: str = "off",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> Path:
    """Trigger one stereo still capture, saved as a combined PNG.

    Raises:
        subprocess.CalledProcessError: rpicam-still exited with an error.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_capture_command(output_path, shutter_us, gain, awb_gains, denoise, width, height, timeout_ms)
    subprocess.run(command, check=True, capture_output=True)
    return output_path


def split_stereo_frame(combined_image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a combined L+R frame into its left and right half.

    Camarray-HAT convention: left camera in the left half, right camera in
    the right half of one combined frame (see docs/decisions.md, 2026-09-02).
    """
    half = combined_image.shape[1] // 2
    return combined_image[:, :half], combined_image[:, half:]
