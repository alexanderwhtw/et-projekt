"""Translation ueber Frame-Index: X und Z (Bodenebene) nebeneinander in zwei
Graphen, analog zu plot_rotation_over_time.py.

Ergaenzt die Top-Down-Karte (plot_trajectory_map.py, X gegen Z) um die
Zeitachse -- zeigt, WANN sich welche Achse wie veraendert, nicht nur die
resultierende Form. Y (Hoehe) wird bewusst weggelassen (Bodenroute, Y ist
ueberwiegend Rauschen/Drift, siehe docs/decisions.md).

Nutzung:
    python scripts/plot_translation_over_time.py --trajectory PATH \
        [--exclude-frames N N ...] [--output PATH]
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument(
        "--exclude-frames", type=int, nargs="*", default=[], metavar="INDEX",
        help="Frame-Indizes, die als Vertikallinien markiert werden (z.B. vom Plausibilitaets-Filter uebersprungene Frames)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Standard: neben der Trajektorie-Datei")
    args = parser.parse_args()

    data = yaml.safe_load(open(args.trajectory))
    positions = np.array(data["positions"])
    n = len(positions)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)

    axes[0].plot(range(n), positions[:, 0], "-o", markersize=4, color="tab:blue")
    axes[0].set_xlabel("Frame-Index")
    axes[0].set_ylabel("X (m)")
    axes[0].set_title("Translation X über die Zeit")
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(0, color="gray", linewidth=0.8)

    axes[1].plot(range(n), positions[:, 2], "-o", markersize=4, color="tab:green")
    axes[1].set_xlabel("Frame-Index")
    axes[1].set_ylabel("Z (m)")
    axes[1].set_title("Translation Z über die Zeit")
    axes[1].grid(True, alpha=0.3)
    axes[1].axhline(0, color="gray", linewidth=0.8)

    for ax in axes:
        for j, f in enumerate(args.exclude_frames):
            ax.axvline(f, color="red", linestyle=":", alpha=0.6, label="übersprungen (Filter)" if j == 0 else None)
        if args.exclude_frames:
            ax.legend(fontsize=8)

    fig.suptitle(f"Translation über die Zeit: {args.trajectory.parent.name}")
    fig.tight_layout()
    output = args.output or args.trajectory.parent / "translation_over_time.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Plot gespeichert: {output}")


if __name__ == "__main__":
    main()
