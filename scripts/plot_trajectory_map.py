"""Visualisiert eine berechnete VO-Trajektorie als 2D-Top-Down-Karte (X-Z-
Ebene, Y/Hoehe ignoriert) und vergleicht sie optional mit Massband-Ground-
Truth-Wegpunkten (data/reference_points.yaml).

Rein nachgelagerter Auswertungs-/Visualisierungs-Output auf Basis bereits
berechneter VO-Ergebnisse -- kein Bestandteil des Lokalisierungsalgorithmus,
keine Laufzeit-Kartennutzung (siehe docs/decisions.md, 2026-09-07). Nutzt
direkt die von scripts/run_vo_sequence.py erzeugte trajectory.yaml.

Einzelne Frames koennen ueber --exclude-frames aus der Darstellung
ausgeschlossen werden, wenn sie bereits als eigenstaendiger, diagnostizierter
Fehlerfall dokumentiert sind (z.B. der Merkmalsschwund-Ausreisser bei 120cm,
siehe docs/decisions.md, 2026-09-08) -- nicht um Fehler allgemein zu
verstecken, sondern um die sonst gute Trajektorie nicht zu verzerren.

Nutzung:
    python scripts/plot_trajectory_map.py \
        --trajectory results/measurements/2026-09-08_vo_sequence_test/trajectory.yaml \
        [--reference-points data/reference_points.yaml] \
        [--exclude-frames 6] \
        [--output PATH]
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_REFERENCE_POINTS = REPO_ROOT / "data" / "reference_points.yaml"


def load_positions(trajectory_path: Path) -> np.ndarray:
    with open(trajectory_path) as f:
        data = yaml.safe_load(f)
    return np.array(data["positions"], dtype=float)


def load_reference_positions(reference_points_path: Path) -> np.ndarray | None:
    if not reference_points_path.exists():
        return None
    with open(reference_points_path) as f:
        data = yaml.safe_load(f)
    points = list(data.get("points", {}).values())
    return np.array(points, dtype=float) if points else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--reference-points", type=Path, default=DEFAULT_REFERENCE_POINTS)
    parser.add_argument(
        "--exclude-frames",
        type=int,
        nargs="*",
        default=[],
        metavar="INDEX",
        help="0-basierte Frame-Indizes, die als bereits diagnostizierte Ausreisser "
        "aus der Darstellung ausgeschlossen werden (grau markiert statt geglaettet)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Standard: neben der Trajektorie-Datei")
    args = parser.parse_args()

    positions = load_positions(args.trajectory)
    n = len(positions)
    excluded = sorted(i for i in args.exclude_frames if 0 <= i < n)
    keep = [i for i in range(n) if i not in excluded]
    plotted = positions[keep]

    ref_positions = load_reference_positions(args.reference_points)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(plotted[:, 0], plotted[:, 2], "-o", color="tab:blue", markersize=5, label="Geschätzt (VO)")

    for j, i in enumerate(excluded):
        ax.scatter(
            positions[i, 0],
            positions[i, 2],
            c="lightgray",
            marker="x",
            s=90,
            zorder=4,
            clip_on=True,
            label="Ausgeschlossen (dokumentierter Ausreißer, außerhalb Achsenbereich möglich)" if j == 0 else None,
        )

    if ref_positions is not None and len(ref_positions) == n:
        ref_plotted = ref_positions[keep]
        ax.plot(
            ref_plotted[:, 0], ref_plotted[:, 2], "--s", color="tab:orange", markersize=5, label="Ground Truth (Maßband)"
        )
    elif ref_positions is not None:
        print(
            f"WARNUNG: {len(ref_positions)} Ground-Truth-Punkte != {n} Trajektorien-Frames "
            "-- Ground Truth wird nicht eingezeichnet."
        )

    ax.scatter(plotted[0, 0], plotted[0, 2], c="green", s=160, marker="*", zorder=5, label="Start")
    ax.scatter(plotted[-1, 0], plotted[-1, 2], c="red", s=140, marker="X", zorder=5, label="Ende")

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_title(f"Top-Down-Trajektorie: {args.trajectory.parent.name}")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    # Legende bewusst ausserhalb der Achsenbox: bei stark laenglichen
    # Trajektorien (equal aspect) wird die Box sonst zu schmal, um Daten +
    # Legende gleichzeitig ueberlappungsfrei darzustellen.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=9)

    # Achsenbereich bewusst nur an den dargestellten (nicht ausgeschlossenen)
    # Punkten ausrichten -- ein Ausreisser soll die eigentliche Trajektorie
    # nicht auf Millimeter-Groesse zusammenstauchen.
    in_view = plotted if ref_positions is None or len(ref_positions) != n else np.vstack([plotted, ref_positions[keep]])
    margin = 0.15 * max(np.ptp(in_view[:, 0]), np.ptp(in_view[:, 2]), 0.5)
    ax.set_xlim(in_view[:, 0].min() - margin, in_view[:, 0].max() + margin)
    ax.set_ylim(in_view[:, 2].min() - margin, in_view[:, 2].max() + margin)

    output = args.output or args.trajectory.parent / "trajectory_map.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Plot gespeichert: {output}")


if __name__ == "__main__":
    main()
