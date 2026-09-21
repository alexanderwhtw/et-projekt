"""Baut eine ground_truth.yaml aus einer Liste gemessener lokaler Bewegungs-
Segmente (reine Drehung ODER reine Translation pro Segment), statt sie von
Hand in Weltkoordinaten umzurechnen.

Hintergrund (siehe docs/decisions.md, 2026-09-21): bisherige ground_truth.yaml-
Dateien waren entweder reine Translation entlang einer festen Achse (Tag 6/11,
triviale Weltkoordinaten) oder reine Rotation an einem festen Punkt (Tag 12).
Fuer eine Route mit mehreren Drehungen + Translationen (z.B. "90 Grad drehen,
geradeaus durch eine Tuer, nochmal drehen, weiter geradeaus") muesste man die
Kamera-Position pro Frame sonst von Hand per Trigonometrie in
Frame-0-Weltkoordinaten umrechnen -- fehleranfaellig und nicht nachvollziehbar.

Stattdessen: dieselbe bereits getestete Verkettungslogik wiederverwenden, die
auch die geschaetzte VO-Trajektorie berechnet (src/localization/trajectory.py::
chain_poses(), siehe tests/test_trajectory.py) -- jedes Segment liefert ein
lokales (R, t)-Paar (Rotation um die Kamera-y-Achse ODER Translation entlang
der aktuellen Kamera-z-Achse/Blickrichtung, nie beides gleichzeitig), chain_poses()
verkettet das exakt so wie die VO-Pipeline ihre eigenen Posen verkettet.

Rotations-Vorzeichenkonvention identisch zu rotation_deg_to_matrix() in
scripts/plot_error_growth.py (empirisch bestimmt, siehe docs/decisions.md,
2026-09-17 Teil 2): R(psi) = cv2.Rodrigues([0, -radians(psi), 0]). Eine
Linksdrehung um `degrees` erhoeht das kumulierte psi um +degrees, eine
Rechtsdrehung senkt es um -degrees -- direction ist also relativ zur
Bewegungsrichtung des Wagens/der Kamera, nicht eine absolute Himmelsrichtung.

Segment-Datei (YAML), z.B. data/vo_sequences/<name>/route_segments.yaml:
    segments:
      - {type: rotate, degrees: 18, direction: left}
      - {type: rotate, degrees: 18, direction: left}
      - {type: translate, meters: 0.25}
      - {type: translate, meters: 0.25}

Ein Segment = ein Frame-Uebergang. Bei N Segmenten entstehen N+1 Frames
(Frame 0 = Startpose, identisch zu chain_poses()' Default-Initialpose).
Reine Auswertungs-/Vorbereitungslogik, kein Bestandteil des
Lokalisierungsalgorithmus, analog zu plot_trajectory_map.py/plot_error_growth.py.

Nutzung:
    python scripts/build_ground_truth.py \
        --segments data/vo_sequences/2026-09-21_flur_route/route_segments.yaml \
        [--output data/vo_sequences/2026-09-21_flur_route/ground_truth.yaml]  # Default: neben --segments
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.localization.trajectory import chain_poses, positions_from_poses  # noqa: E402


def rotation_deg_to_matrix(angle_deg: float) -> np.ndarray:
    """Identisch zu scripts/plot_error_growth.py::rotation_deg_to_matrix() --
    kumulierter Gier-Winkel (Kamera-y-Achse, siehe docs/decisions.md,
    2026-09-17) -> Rotationsmatrix."""
    R, _ = cv2.Rodrigues(np.array([0.0, -np.radians(angle_deg), 0.0]))
    return R


def build_relative_poses(segments: list[dict]) -> tuple[list[tuple[np.ndarray, np.ndarray]], list[float]]:
    """Segmente -> (relative_poses fuer chain_poses(), kumulierte rotations_deg je Frame inkl. Frame 0)."""
    relative_poses = []
    cumulative_deg = [0.0]
    psi = 0.0
    for seg in segments:
        if seg["type"] == "rotate":
            sign = 1.0 if seg["direction"] == "left" else -1.0
            delta_deg = sign * seg["degrees"]
            # Alle Drehungen erfolgen um dieselbe feste Kamera-y-Achse (reine
            # Gierdrehung, kein Rollen/Nicken) -- solche Rotationen kommutieren,
            # die lokale Schritt-Rotation ist deshalb direkt rotation_deg_to_matrix(delta_deg),
            # unabhaengig vom bisherigen kumulierten Winkel psi.
            R = rotation_deg_to_matrix(delta_deg)
            t = np.zeros(3)
            psi += delta_deg
        elif seg["type"] == "translate":
            R = np.eye(3)
            t = np.array([0.0, 0.0, seg["meters"]])
        else:
            raise ValueError(f"Unbekannter Segmenttyp: {seg['type']!r} (erwartet 'rotate' oder 'translate')")
        relative_poses.append((R, t))
        cumulative_deg.append(psi)
    return relative_poses, cumulative_deg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--segments", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None, help="Default: ground_truth.yaml neben --segments")
    args = parser.parse_args()

    with open(args.segments) as f:
        segments = yaml.safe_load(f)["segments"]

    relative_poses, cumulative_deg = build_relative_poses(segments)
    poses = chain_poses(relative_poses)
    positions = positions_from_poses(poses)

    n = len(positions)
    width = len(str(n - 1))
    keys = [f"frame_{i:0{width}d}" for i in range(n)]

    output = args.output or args.segments.parent / "ground_truth.yaml"
    with open(output, "w") as f:
        f.write(
            "# Automatisch generiert aus Bewegungs-Segmenten (siehe "
            f"{args.segments.name}) via scripts/build_ground_truth.py --\n"
            "# NICHT von Hand editieren, stattdessen die Segment-Datei anpassen und neu generieren.\n"
            "# Achsenkonvention: OpenCV-Kamerakonvention (x=rechts, y=unten, z=in die Szene hinein),\n"
            "# Ursprung = erste Kameraposition/Frame 0. rotations_deg-Vorzeichenkonvention siehe\n"
            "# docs/decisions.md (2026-09-17 Teil 2, 2026-09-21).\n"
        )
        yaml.safe_dump(
            {
                "points": {k: p.tolist() for k, p in zip(keys, positions)},
                "rotations_deg": dict(zip(keys, cumulative_deg)),
            },
            f,
            default_flow_style=None,
            sort_keys=False,
        )
    print(f"{n} Frames, Ground-Truth gespeichert: {output}")


if __name__ == "__main__":
    main()
