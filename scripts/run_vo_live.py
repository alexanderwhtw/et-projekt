"""Live-VO: Kamera-Trigger + sofortige Verarbeitung mit laufender
Trajektorien-Ausgabe (siehe CHECKLIST.md, Tag 12; docs/decisions.md,
2026-09-08/2026-09-16).

Gegenstueck zu run_vo_sequence.py: statt bereits aufgenommene Bilder von der
Platte zu laden (load_rectified()), wird pro Schleifendurchlauf ein echter
Kamera-Trigger ausgeloest (src.capture.session.capture_indexed_pair(), wie
bei scripts/capture_vo_frame.py). Die Verarbeitungs-Primitive
(init_vo_step()/step_vo_pipeline()) und die Frame-fuer-Frame-Schleife sind
identisch zu run_vo_sequence.py -- Batch- und Live-Betrieb koennen dadurch
nicht auseinanderlaufen (siehe docs/decisions.md, Live-VO-Umstellung).

Aufnahme-Latenz-Benchmark (2026-09-17, Pi, 5 Wiederholungen): eine
rpicam-still-Aufnahme braucht ~1.4-1.6s (Mittel 1.46s), die VO-Verarbeitung
pro Frame (Feature-Detektion+Matching+Triangulation+Pose-Schaetzung)
~0.24s -- die Aufnahme dominiert deutlich. Kein fester Sleep-Takt zwischen
den Frames: solange kein motorisierter Wagen existiert (siehe
docs/decisions.md, 2026-09-08, "Ausblick"), bewegt ein Mensch die Kamera
zwischen den Aufnahmen -- daher standardmaessig interaktiv (Enter-Taste
loest die naechste Aufnahme aus). Ein optionaler `--interval`-Parameter
erlaubt einen automatischen Takt fuer einen spaeteren kamerafuehrungslosen
Aufbau; muss dafuer > Aufnahme+Verarbeitungs-Zeit (~1.7s) liegen, sonst
ueberlappen sich Aufnahmen.

Frames werden wie bei capture_vo_frame.py persistiert (Nachvollziehbarkeit,
CLAUDE.md) -- keine reine In-Memory-Verarbeitung ohne Bildspuren.

MUSS auf dem Pi laufen (braucht rpicam-still + die echte Kamera).

Nutzung:
    python scripts/run_vo_live.py --sequence-dir data/vo_sequences/<name> \
                                   --n-frames 5 \
                                   [--calibration results/calibration/2026-09-15_calibration.yaml] \
                                   [--shutter 10000] [--gain 1.0] \
                                   [--interval 2.0]  # Default: interaktiv (Enter-Taste)
                                   [--seed 0]
"""

import argparse
import signal
import sys
import time
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.calibration.io import load_calibration_result  # noqa: E402
from src.calibration.rectification import compute_rectification_maps  # noqa: E402
from src.capture.sequence import build_frame_paths  # noqa: E402
from src.capture.session import capture_indexed_pair  # noqa: E402
from src.localization.vo_pipeline import init_vo_step, step_vo_pipeline  # noqa: E402

DEFAULT_CALIBRATION = REPO_ROOT / "results" / "calibration" / "2026-09-15_calibration.yaml"
RESULTS_DIR = REPO_ROOT / "results" / "measurements"
MANIFEST_FIELDNAMES = ["index", "notiz", "shutter", "gain", "timestamp"]


def _raise_keyboard_interrupt(signum, frame):
    raise KeyboardInterrupt


def main() -> None:
    # SIGINT is ignored by design for background jobs started from a
    # non-interactive shell (e.g. `nohup ... & disown` over ssh, see
    # docs/decisions.md, 2026-09-17) -- plain `kill <pid>` (SIGTERM) is not
    # affected by that and is the reliable way to stop a background live-VO
    # run, so it needs the same graceful-stop handling as Ctrl+C.
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sequence-dir", type=Path, required=True)
    parser.add_argument("--n-frames", type=int, required=True)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--shutter", type=int, default=10000)
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Sekunden automatischer Sleep zwischen Aufnahmen. Default: interaktiv "
        "(Enter-Taste), da die Kamera bisher von Hand zwischen Aufnahmen bewegt wird.",
    )
    parser.add_argument("--seed", type=int, default=0, help="RANSAC-Seed fuer reproduzierbare Ergebnisse (Default: 0)")
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

    def capture_and_rectify(frame_index: int) -> tuple[np.ndarray, np.ndarray]:
        seq_index = capture_indexed_pair(
            args.sequence_dir,
            args.shutter,
            args.gain,
            MANIFEST_FIELDNAMES,
            extra_manifest_fields={"notiz": f"live frame {frame_index}"},
        )
        left_path, right_path = build_frame_paths(args.sequence_dir, seq_index)
        left = cv2.imread(str(left_path), cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(str(right_path), cv2.IMREAD_GRAYSCALE)
        left_rect = cv2.remap(left, map_x_L, map_y_L, cv2.INTER_LINEAR)
        right_rect = cv2.remap(right, map_x_R, map_y_R, cv2.INTER_LINEAR)
        return left_rect, right_rect

    print(f"Live-VO: {args.n_frames} Frames, Ziel {args.sequence_dir}.")
    poses = []
    try:
        for frame_index in range(args.n_frames):
            if frame_index > 0:
                if args.interval is not None:
                    time.sleep(args.interval)
                else:
                    input(f"Kamera bewegen, dann Enter fuer Frame {frame_index}: ")

            t0 = time.monotonic()
            image_L, image_R = capture_and_rectify(frame_index)

            if frame_index == 0:
                pose, points, descriptors = init_vo_step(image_L, image_R, P_L, P_R)
            else:
                try:
                    pose, points, descriptors = step_vo_pipeline(
                        image_L, image_R, P_L, P_R, pose, points, descriptors, seed=args.seed
                    )
                except RuntimeError as e:
                    print(f"Frame {frame_index}: {e} -- Live-VO gestoppt, bisherige Trajektorie wird gespeichert.")
                    break
            elapsed = time.monotonic() - t0
            poses.append(pose)
            print(f"  Frame {frame_index}: [{pose[0, 3]:+.4f}, {pose[1, 3]:+.4f}, {pose[2, 3]:+.4f}]  ({elapsed:.2f}s)")
    except KeyboardInterrupt:
        print("\nAbgebrochen (Strg+C) -- bisherige Trajektorie wird gespeichert.")

    if not poses:
        print("Keine Frames verarbeitet, kein Ergebnis gespeichert.")
        return

    positions = [pose[:3, 3].tolist() for pose in poses]
    rotations = [pose[:3, :3].tolist() for pose in poses]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    output_path = RESULTS_DIR / f"{today}_vo_live_test" / "trajectory.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(
            {
                "sequence_dir": str(args.sequence_dir),
                "calibration": str(args.calibration),
                "seed": args.seed,
                "positions": positions,
                "rotations": rotations,
            },
            f,
            default_flow_style=None,
            sort_keys=False,
        )
    print(f"\nErgebnis gespeichert: {output_path}")


if __name__ == "__main__":
    main()
