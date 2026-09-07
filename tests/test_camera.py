from unittest.mock import patch

import numpy as np

from src.capture.camera import build_capture_command, capture_frame, split_stereo_frame


def test_build_capture_command_contains_settings():
    command = build_capture_command("/tmp/out.png", shutter_us=10000, gain=1.0, awb_gains=(1.0, 1.0), denoise="off")

    assert command[0] == "rpicam-still"
    assert "-n" in command
    assert "--shutter" in command and command[command.index("--shutter") + 1] == "10000"
    assert "--gain" in command and command[command.index("--gain") + 1] == "1.0"
    assert "--awbgains" in command and command[command.index("--awbgains") + 1] == "1.0,1.0"
    assert "--denoise" in command and command[command.index("--denoise") + 1] == "off"
    assert "--width" in command and command[command.index("--width") + 1] == "2560"
    assert "--height" in command and command[command.index("--height") + 1] == "800"
    assert "-o" in command and command[command.index("-o") + 1] == "/tmp/out.png"


def test_capture_frame_invokes_rpicam_still_with_built_command(tmp_path):
    output_path = tmp_path / "session" / "frame.png"

    with patch("src.capture.camera.subprocess.run") as mock_run:
        result = capture_frame(output_path, shutter_us=10000, gain=1.0)

    assert result == output_path
    assert output_path.parent.is_dir()  # parent dir created even though rpicam-still itself is mocked
    mock_run.assert_called_once()
    called_command = mock_run.call_args.args[0]
    assert called_command == build_capture_command(output_path, shutter_us=10000, gain=1.0)
    assert mock_run.call_args.kwargs["check"] is True


def test_split_stereo_frame_splits_in_half():
    left_half = np.full((100, 200), 10, dtype=np.uint8)
    right_half = np.full((100, 200), 200, dtype=np.uint8)
    combined = np.hstack([left_half, right_half])

    left, right = split_stereo_frame(combined)

    assert left.shape == (100, 200)
    assert right.shape == (100, 200)
    np.testing.assert_array_equal(left, left_half)
    np.testing.assert_array_equal(right, right_half)
